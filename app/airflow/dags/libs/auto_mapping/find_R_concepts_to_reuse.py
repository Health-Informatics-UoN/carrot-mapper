import logging

from airflow.providers.postgres.hooks.postgres import PostgresHook
from libs.queries import (
    create_reuse_concept_query,
    create_temp_reuse_table_query,
    find_m_concepts_query,
    find_m_concepts_query_field_level,
    find_object_id_query,
    validate_reused_concepts_query,
)
from libs.settings import AIRFLOW_DAGRUN_TIMEOUT
from libs.utils import (
    JobStageType,
    StageStatusType,
    pull_validated_params,
    update_job_status,
)

# PostgreSQL connection hook
pg_hook = PostgresHook(
    postgres_conn_id="postgres_db_conn",
    options=f"-c statement_timeout={float(AIRFLOW_DAGRUN_TIMEOUT) * 60 * 1000}ms",
)


def delete_R_concepts(**kwargs) -> None:
    """
    To make sure the eligble concepts for reusing is up-to-date, we will refresh the R concepts
    by deleting all reused concepts for a given scan report table with creation type 'R' (Reused),
    in both cases of trigger_reuse_concepts is True or False.

    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")

    try:
        table_id = validated_params["table_id"]
        delete_reused_concepts = """
            DELETE FROM mapping_scanreportconcept
            WHERE creation_type = 'R' 
            AND (
                -- Delete concepts for fields in this table
                (content_type_id = (
                    SELECT id FROM django_content_type 
                    WHERE app_label = 'mapping' AND model = 'scanreportfield'
                ) AND object_id IN (
                    SELECT srf.id 
                    FROM mapping_scanreportfield AS srf
                    WHERE srf.scan_report_table_id = %(table_id)s
                ))
                OR 
                -- Delete concepts for values in this table
                (content_type_id = (
                    SELECT id FROM django_content_type 
                    WHERE app_label = 'mapping' AND model = 'scanreportvalue'
                ) AND object_id IN (
                    SELECT srv.id
                    FROM mapping_scanreportvalue AS srv
                    JOIN mapping_scanreportfield AS srf ON srv.scan_report_field_id = srf.id
                    WHERE srf.scan_report_table_id = %(table_id)s
                ))
            );
        """
        pg_hook.run(delete_reused_concepts, parameters={"table_id": table_id})

    except Exception as e:
        logging.error(f"Error in delete_R_concepts: {str(e)}")
        raise e


def find_matching_value(**kwargs):
    """
    Identifies and extracts field values from completed scan reports that have M-type concepts tied to them.

    This function locates field values in eligible scan reports that have manually added (M-type) concepts
    within the same parent dataset. The process:
    1. Finds eligible scan reports (completed, not hidden, in same dataset, not current report)
    2. Finds tables in those reports with the same name as the current table
    3. Finds values in those tables that have M-type concepts tied to them
    4. Inserts those values into temp_reuse_concepts for further processing
    5. Find the object_id for each reuse concept by matching with current table values

    Results are stored in a temporary table (temp_reuse_concepts_{table_id}) for further processing.

    Required parameters (pulled from XCom):
        - table_id (int): ID of the scan report table being processed
        - parent_dataset_id (int): ID of the parent dataset to search within
        - scan_report_id (int): ID of the current scan report
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")
    trigger_reuse_concepts = validated_params["trigger_reuse_concepts"]

    if trigger_reuse_concepts:
        parent_dataset_id = validated_params["parent_dataset_id"]
        table_id = validated_params["table_id"]
        scan_report_id = validated_params["scan_report_id"]

        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.REUSE_CONCEPTS,
            status=StageStatusType.IN_PROGRESS,
            details="Finding eligible concepts for reuse at the value level",
        )

        # Create temp table for reuse concepts
        try:
            pg_hook.run(
                create_temp_reuse_table_query, parameters={"table_id": table_id}
            )
            logging.info(f"Successfully created temp_reuse_concepts_{table_id} table")
        except Exception as e:
            logging.error(
                f"Failed to create temp_reuse_concepts_{table_id} table: {str(e)}"
            )
            raise e

        try:
            # Get the current table name to find matching tables in eligible scan reports
            get_current_table_name_query = """
            SELECT name FROM mapping_scanreporttable WHERE id = %(table_id)s;
            """
            current_table_name = pg_hook.get_first(
                get_current_table_name_query, parameters={"table_id": table_id}
            )[0]
            # Find M-type concepts for reuse at the value level
            pg_hook.run(
                find_m_concepts_query,
                parameters={
                    "table_id": table_id,
                    "parent_dataset_id": parent_dataset_id,
                    "scan_report_id": scan_report_id,
                    "current_table_name": current_table_name,
                },
            )
            logging.info(
                "Successfully found M-type concepts for reuse at the value level"
            )
        except Exception as e:
            logging.error(
                f"Failed to find M-type concepts for reuse at the value level: {str(e)}"
            )
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.REUSE_CONCEPTS,
                status=StageStatusType.FAILED,
                details=f"Error when finding M-type concepts for reuse at the value level: {str(e)}",
            )
            raise e
    else:
        logging.info("Skipping find_matching_value as trigger_reuse_concepts is False")


def find_matching_field(**kwargs):
    """
    Finds matching fields in previously completed scan reports that can be reused for concept mapping.

    This function identifies fields in the current table that match fields in other scan reports
    which already have concepts assigned. It identifies matching fields by name and inserts them
    into the temporary reuse concepts table for later processing.

    The function prioritizes concepts from the oldest scan report when duplicates are found.

    Required parameters (pulled from XCom):
        - table_id (int): ID of the scan report table being processed
        - parent_dataset_id (int): ID of the parent dataset to search within
        - scan_report_id (int): ID of the current scan report
        - has_data_dictionary (bool): If True, V-type concepts will be excluded from reuse
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")
    trigger_reuse_concepts = validated_params["trigger_reuse_concepts"]

    if trigger_reuse_concepts:
        parent_dataset_id = validated_params["parent_dataset_id"]
        table_id = validated_params["table_id"]
        scan_report_id = validated_params["scan_report_id"]

        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.REUSE_CONCEPTS,
            status=StageStatusType.IN_PROGRESS,
            details="Finding eligible concepts for reuse at the field level",
        )

        try:
            # Get the current table name to find matching tables in eligible scan reports
            get_current_table_name_query = """
            SELECT name FROM mapping_scanreporttable WHERE id = %(table_id)s;
            """
            current_table_name = pg_hook.get_first(
                get_current_table_name_query, parameters={"table_id": table_id}
            )[0]
            # Find M-type concepts for reuse at the field level
            pg_hook.run(
                find_m_concepts_query_field_level,
                parameters={
                    "table_id": table_id,
                    "parent_dataset_id": parent_dataset_id,
                    "scan_report_id": scan_report_id,
                    "current_table_name": current_table_name,
                },
            )
            logging.info(
                "Successfully found M-type concepts for reuse at the field level"
            )
        except Exception as e:
            logging.error(
                f"Failed to find M-type concepts for reuse at the field level: {str(e)}"
            )
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.REUSE_CONCEPTS,
                status=StageStatusType.FAILED,
                details=f"Error when finding M-type concepts for reuse at the field level: {str(e)}",
            )
            raise e
    else:
        logging.info("Skipping find_matching_field as trigger_reuse_concepts is False")


def create_reusing_concepts(**kwargs):
    """
    Find object ids for reusing concepts and create R concepts for a given scan report table.
    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    - scan_report_id (int): The ID of the scan report to process
    """

    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")
    trigger_reuse_concepts = validated_params["trigger_reuse_concepts"]
    scan_report_id = validated_params["scan_report_id"]
    table_id = validated_params["table_id"]

    if trigger_reuse_concepts:
        #  Find object ids for reusing concepts
        try:
            pg_hook.run(
                find_object_id_query,
                parameters={"table_id": table_id},
            )
            logging.info("Successfully found object ids for reusing concepts")
        except Exception as e:
            logging.error(f"Failed to find object ids for reusing concepts: {str(e)}")
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.REUSE_CONCEPTS,
                status=StageStatusType.FAILED,
                details=f"Error when finding object ids for reusing concepts: {str(e)}",
            )
            raise e
        #  Validate reused concepts
        try:
            pg_hook.run(
                validate_reused_concepts_query,
                parameters={"table_id": table_id},
            )
            logging.info("Successfully validated reused concepts")
        except Exception as e:
            logging.error(f"Failed to validate reused concepts: {str(e)}")
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.REUSE_CONCEPTS,
                status=StageStatusType.FAILED,
                details=f"Error when validating reused concepts: {str(e)}",
            )
            raise e
        #  Create R concepts
        try:
            pg_hook.run(create_reuse_concept_query, parameters={"table_id": table_id})
            logging.info("Successfully created R (Reused) concepts")
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.REUSE_CONCEPTS,
                status=StageStatusType.COMPLETE,
                details="R (Reused) concepts successfully created from matching fields and values",
            )
        except Exception as e:
            logging.error(f"Database error in create_standard_concepts: {str(e)}")
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.REUSE_CONCEPTS,
                status=StageStatusType.FAILED,
                details=f"Error when creating R (Reused) concepts: {str(e)}",
            )
            raise e
    else:
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.REUSE_CONCEPTS,
            status=StageStatusType.COMPLETE,
            details="Skipped creating R (Reused) concepts because of user's preference",
        )

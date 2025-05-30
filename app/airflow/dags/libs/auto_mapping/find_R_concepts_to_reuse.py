from libs.utils import (
    update_job_status,
    JobStageType,
    StageStatusType,
    pull_validated_params,
)
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging
from libs.queries import (
    find_reusing_value_query,
    find_reusing_field_query,
    find_object_id_query,
)

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def delete_R_concepts(**kwargs) -> None:
    """
    To make sure the eligble concepts for reusing is up-to-date, we will refresh the R concepts
    by deleting all reused concepts for a given scan report table with creation type 'R' (Reused).
    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")
    trigger_reuse_concepts = validated_params["trigger_reuse_concepts"]

    if trigger_reuse_concepts:
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
            logging.error(f"Error in delete_mapping_rules: {str(e)}")
            raise
    else:
        logging.info("Skipping delete_R_concepts as trigger_reuse_concepts is False")


def find_matching_value(**kwargs):
    """
    Identifies and extracts field values from completed scan reports that can be reused for concept mapping.

    This function locates field values in the current table that match values in previously mapped scan reports
    within the same parent dataset. The matching process requires:
    1. Exact value text matching
    2. Matching value descriptions (or both NULL)
    3. Values must belong to fields with the same name

    The SQL procedure:
    1. Starts with values in the current scan report table
    2. Joins to values in other scan reports based on value name, description, and field name
    3. Finds values with associated concepts in completed scan reports
    4. Filters to values from the specified parent dataset and only from completed scan reports
    5. Excludes already reused concepts (creation_type != 'R')
    6. Optionally excludes concepts from vocabulary matching (creation_type != 'V') if a data dictionary exists
    7. Removes duplicate matches, keeping only the match from the oldest scan report

    Results are stored in a temporary table (temp_reuse_concepts_{table_id}) for further processing.

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
            details=f"Finding eligible concepts for reuse at the value level",
        )

        # Create temp table for reuse concepts
        create_table_query = """
        -- Prevent duplicate creation of the temp reuse concepts table, in case of re-running the DAG after a bug fix
        DROP TABLE IF EXISTS temp_reuse_concepts_%(table_id)s;
        CREATE TABLE temp_reuse_concepts_%(table_id)s (
            object_id INTEGER,
            matching_value_name TEXT,
            matching_field_name TEXT,
            matching_table_name TEXT,
            -- TODO: we need to add source_scanreport_id for the model SCANREPORTCONCEPT as well for R concepts
            source_scanreport_id INTEGER,
            content_type_id INTEGER,
            source_concept_id INTEGER,
            standard_concept_id INTEGER
        );
        """
        try:
            pg_hook.run(create_table_query, parameters={"table_id": table_id})
            logging.info(
                f"Successfully created temp_standard_concepts_{table_id} table"
            )
        except Exception as e:
            logging.error(
                f"Failed to create temp_standard_concepts_{table_id} table: {str(e)}"
            )
            raise

        # When a data dictionary (or field_vocab_pairs) for a table is provided, we won't reuse V concepts,
        # because that is the job of V concepts DAG
        field_vocab_pairs = validated_params["field_vocab_pairs"]
        exclude_v_concepts_condition = (
            "AND esc.creation_type != 'V'" if field_vocab_pairs else ""
        )

        try:
            # NOTE: parameterizing the query is not working for the exclude_v_concepts_condition, so we are using string interpolation instead
            pg_hook.run(
                find_reusing_value_query
                % {
                    "table_id": table_id,
                    "parent_dataset_id": parent_dataset_id,
                    "scan_report_id": scan_report_id,
                    "exclude_v_concepts_condition": exclude_v_concepts_condition,
                }
            )
            logging.info(f"Successfully found reusing concepts at the value level")
        except Exception as e:
            logging.error(
                f"Failed to find reusing concepts at the value level: {str(e)}"
            )
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.REUSE_CONCEPTS,
                status=StageStatusType.FAILED,
                details=f"Error when finding eligible concepts for reuse at the value level",
            )
            raise
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
            details=f"Finding eligible concepts for reuse at the field level",
        )

        try:
            pg_hook.run(
                find_reusing_field_query,
                parameters={
                    "table_id": table_id,
                    "parent_dataset_id": parent_dataset_id,
                    "scan_report_id": scan_report_id,
                },
            )
            logging.info(f"Successfully found reusing concepts at the field level")
        except Exception as e:
            logging.error(
                f"Failed to find reusing concepts at the value level: {str(e)}"
            )
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.REUSE_CONCEPTS,
                status=StageStatusType.FAILED,
                details=f"Error when finding eligible concepts for reuse at the field level",
            )
            raise
    else:
        logging.info("Skipping find_matching_field as trigger_reuse_concepts is False")


def find_object_id(**kwargs):
    """
    Find object ids for reusing concepts.
    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    - scan_report_id (int): The ID of the scan report to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")
    trigger_reuse_concepts = validated_params["trigger_reuse_concepts"]

    if trigger_reuse_concepts:
        scan_report_id = validated_params["scan_report_id"]
        table_id = validated_params["table_id"]

        try:
            pg_hook.run(
                find_object_id_query,
                parameters={"table_id": table_id, "scan_report_id": scan_report_id},
            )
            logging.info(f"Successfully found object ids for reusing concepts")
        except Exception as e:
            logging.error(f"Failed to find object ids for reusing concepts: {str(e)}")
            raise
    else:
        logging.info("Skipping find_object_id as trigger_reuse_concepts is False")


def create_reusing_concepts(**kwargs):
    """
    Create R concepts for a given scan report table.
    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    - scan_report_id (int): The ID of the scan report to process
    """

    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")
    trigger_reuse_concepts = validated_params["trigger_reuse_concepts"]

    if trigger_reuse_concepts:
        table_id = validated_params["table_id"]
        scan_report_id = validated_params["scan_report_id"]

        # TODO: when source_concept_id is added to the model SCANREPORTCONCEPT, we need to update the query belowto solve the issue #1006
        create_concept_query = """
            -- Insert standard concepts for field values (only if they don't already exist)
            INSERT INTO mapping_scanreportconcept (
                created_at,
                updated_at,
                object_id,
                creation_type,
                -- TODO: Will have the standard_concept_id (nullable) here
                concept_id,
                content_type_id
            )
            SELECT
                NOW(),
                NOW(),
                temp_reuse_concepts.object_id,
                'R',       -- Creation type: Reused
                -- TODO: if standard_concept_id is null then we need to use the source_concept_id
                -- TODO: add standard_concept_id here for the newly creted SR concepts
                temp_reuse_concepts.source_concept_id,
                temp_reuse_concepts.content_type_id -- content_type_id for scanreportvalue
            FROM temp_reuse_concepts_%(table_id)s AS temp_reuse_concepts;     
            """

        try:
            pg_hook.run(create_concept_query, parameters={"table_id": table_id})
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
                details=f"Error when creating R (Reused) concepts",
            )
            raise
    else:
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.REUSE_CONCEPTS,
            status=StageStatusType.COMPLETE,
            details="Skipped creating R (Reused) concepts because of user's preference",
        )

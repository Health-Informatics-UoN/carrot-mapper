from libs.utils import (
    update_job_status,
    JobStageType,
    StageStatusType,
    pull_validated_params,
)
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging
from libs.queries import (
    create_existing_concepts_table_query,
    find_existing_concepts_query,
    find_source_field_id_query,
)

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def delete_mapping_rules(**kwargs) -> None:
    """
    Delete all mapping rules for a given scan report table.
    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")
    table_id = validated_params["table_id"]
    try:
        delete_query = """
        DELETE FROM mapping_mappingrule
        WHERE source_field_id IN (
            SELECT id FROM mapping_scanreportfield
            WHERE scan_report_table_id = %(table_id)s
        );
        """
        pg_hook.run(delete_query, parameters={"table_id": table_id})
    except Exception as e:
        logging.error(f"Error in delete_mapping_rules: {str(e)}")
        raise ValueError(f"Error in delete_mapping_rules: {str(e)}")


def find_existing_concepts(**kwargs) -> None:
    """
    Find all existing concepts for a given scan report table.
    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")
    table_id = validated_params["table_id"]
    scan_report_id = validated_params["scan_report_id"]

    # Create the temporary table for all existing concepts
    try:
        pg_hook.run(
            create_existing_concepts_table_query, parameters={"table_id": table_id}
        )
        logging.info(f"Successfully created temp_existing_concepts_{table_id} table")
    except Exception as e:
        logging.error(
            f"Failed to create temp_existing_concepts_{table_id} table: {str(e)}"
        )
        raise e

    update_job_status(
        scan_report=scan_report_id,
        scan_report_table=table_id,
        stage=JobStageType.GENERATE_RULES,
        status=StageStatusType.IN_PROGRESS,
        details=f"Retrieving all existing concepts in the scan report table",
    )

    try:
        pg_hook.run(
            find_existing_concepts_query + find_source_field_id_query,
            parameters={"table_id": table_id, "scan_report_id": scan_report_id},
        )
        logging.info(f"Successfully found existing concepts")
    except Exception as e:
        logging.error(f"Failed to find existing concepts: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.GENERATE_RULES,
            status=StageStatusType.FAILED,
            details=f"Error when finding existing concepts",
        )
        raise

from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging
from airflow.exceptions import AirflowException
from libs.utils import (
    update_job_status,
    JobStageType,
    StageStatusType,
    pull_validated_params,
)
from libs.settings import AIRFLOW_DEBUG_MODE, AIRFLOW_DAGRUN_TIMEOUT


# PostgreSQL connection hook
pg_hook = PostgresHook(
    postgres_conn_id="postgres_db_conn",
    options=f"-c statement_timeout={float(AIRFLOW_DAGRUN_TIMEOUT) * 60 * 1000}ms",
)


def create_mapping_rules(**kwargs) -> None:
    """
    Create mapping rules in the mapping_mappingrule table for each record in temp_existing_concepts.
    Each record can generate multiple mapping rules based on the provided rules criteria.

    Validated params needed are:
    - scan_report_id (int): The ID of the scan report to process
    - table_id (int): The ID of the scan report table to process
    - date_event_field (int): The ID of the date event field
    - person_id_field (int): The ID of the person ID field
    """

    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")

    scan_report_id = validated_params["scan_report_id"]
    table_id = validated_params["table_id"]
    date_field_id = validated_params["date_event_field"]
    person_id_field = validated_params["person_id_field"]

    update_job_status(
        scan_report=scan_report_id,
        scan_report_table=table_id,
        stage=JobStageType.GENERATE_RULES,
        status=StageStatusType.IN_PROGRESS,
        details="Creating mapping rules for existing concepts...",
    )

    # Create comprehensive single mapping rule query to handle all rules at once
    mapping_rule_query = """
    INSERT INTO mapping_mappingrule (
        created_at, updated_at, omop_field_id, source_field_id, concept_id, scan_report_id, approved
    )
    SELECT 
        NOW(), NOW(), field_id, source_id, sr_concept_id, %(scan_report_id)s, TRUE
    FROM temp_existing_concepts_%(table_id)s AS temp_table
    CROSS JOIN LATERAL (
        VALUES 
            (dest_person_field_id, %(person_id_field)s),
            (dest_date_field_id, %(date_field_id)s),
            (dest_start_date_field_id, %(date_field_id)s),
            (dest_end_date_field_id, %(date_field_id)s),
            (dest_concept_field_id, source_field_id),
            (omop_source_concept_field_id, source_field_id),
            (omop_source_value_field_id, source_field_id),
            (value_as_string_field_id, source_field_id),
            (value_as_number_field_id, source_field_id)
    ) AS field_mapping(field_id, source_id)
    WHERE field_id IS NOT NULL
    ORDER BY object_id;
    """

    try:
        pg_hook.run(
            mapping_rule_query,
            parameters={
                "table_id": table_id,
                "scan_report_id": scan_report_id,
                "date_field_id": date_field_id,
                "person_id_field": person_id_field,
            },
        )
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.GENERATE_RULES,
            status=StageStatusType.COMPLETE,
            details="Successfully (re-)created mapping rules for all existing concepts",
        )
        if AIRFLOW_DEBUG_MODE == "true":
            return
        # Clean up if not in debug mode
        pg_hook.run(
            """
            DROP TABLE IF EXISTS temp_existing_concepts_%(table_id)s;
            DROP TABLE IF EXISTS temp_standard_concepts_%(table_id)s;
            DROP TABLE IF EXISTS temp_reuse_concepts_%(table_id)s;
            """,
            parameters={"table_id": table_id},
        )

    except Exception as e:
        logging.error(f"Database error in create_mapping_rules: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.GENERATE_RULES,
            status=StageStatusType.FAILED,
            details=f"Error when creating mapping rules for existing concepts: {str(e)}",
        )
        raise AirflowException(f"Database error in create_mapping_rules: {str(e)}")

from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging
from airflow.exceptions import AirflowException
from libs.utils import (
    update_job_status,
    JobStageType,
    StageStatusType,
    pull_validated_params,
    delete_mapping_rules,
)

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def create_mapping_rules(**kwargs) -> None:
    """
    Create mapping rules in the mapping_mappingrule table for each record in temp_reusing_concepts.
    Each record can generate multiple mapping rules based on the provided rules criteria.

    Validated params needed are:
    - scan_report_id (int): The ID of the scan report to process
    - table_id (int): The ID of the scan report table to process
    - date_event_field (int): The ID of the date event field
    - person_id_field (int): The ID of the person ID field
    """
    try:
        # Get validated parameters from XCom
        validated_params = pull_validated_params(kwargs, "validate_params_R_concepts")

        scan_report_id = validated_params["scan_report_id"]
        table_id = validated_params["table_id"]
        date_field_id = validated_params["date_event_field"]
        person_id_field = validated_params["person_id_field"]

        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.GENERATE_RULES,
            status=StageStatusType.IN_PROGRESS,
            details="Creating mapping rules...",
        )

        # Create comprehensive single mapping rule query to handle all rules at once
        mapping_rule_query = f"""
        INSERT INTO mapping_mappingrule (
            created_at, updated_at, omop_field_id, source_field_id, concept_id, scan_report_id, approved
        )
        SELECT 
            NOW(), NOW(), field_id, source_id, sr_concept_id, {scan_report_id}, TRUE
        FROM temp_reuse_concepts_{table_id} AS temp_table
        CROSS JOIN LATERAL (
            VALUES 
                (dest_person_field_id, {person_id_field}),
                (dest_date_field_id, {date_field_id}),
                (dest_start_date_field_id, {date_field_id}),
                (dest_end_date_field_id, {date_field_id}),
                (source_concept_field_id, temp_table.target_source_field_id),
                (dest_concept_field_id, temp_table.target_source_field_id),
                (source_value_field_id, temp_table.target_source_field_id),
                (value_as_string_field_id, temp_table.target_source_field_id),
                (value_as_number_field_id, temp_table.target_source_field_id)
        ) AS field_mapping(field_id, source_id)
        WHERE field_id IS NOT NULL
        ORDER BY object_id;
        """

        try:
            result = pg_hook.run(mapping_rule_query)
            logging.info(
                "Successfully created all mapping rules for each standard concept"
            )
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.GENERATE_RULES,
                status=StageStatusType.COMPLETE,
                details="Successfully created mapping rules",
            )
            return result
        except Exception as e:
            logging.error(f"Database error in create_mapping_rules: {str(e)}")
            raise AirflowException(f"Database error in create_mapping_rules: {str(e)}")
    except Exception as e:
        logging.error(f"Error in create_mapping_rules: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.GENERATE_RULES,
            status=StageStatusType.FAILED,
            details=f"Error in create_mapping_rules: {str(e)}",
        )
        raise AirflowException(f"Error in create_mapping_rules: {str(e)}")

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


def delete_V_mapping_rules(**kwargs) -> None:
    """
    Delete all mapping rules for a given scan report table with creation type 'V' (Built from Vocab).
    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    """
    try:
        # Get validated parameters from XCom
        validated_params = pull_validated_params(kwargs, "validate_params_V_concepts")

        table_id = validated_params["table_id"]
        delete_mapping_rules(table_id, "V")

    except Exception as e:
        logging.error(f"Error in delete_V_mapping_rules: {str(e)}")
        raise AirflowException(f"Error in delete_V_mapping_rules: {str(e)}")


def create_mapping_rules(**kwargs) -> None:
    """
    Create mapping rules in the mapping_mappingrule table for each record in temp_standard_concepts.
    Each record can generate multiple mapping rules based on the provided rules criteria.

    Validated params needed are:
    - scan_report_id (int): The ID of the scan report to process
    - table_id (int): The ID of the scan report table to process
    - field_vocab_pairs (list): List of dictionaries containing field-vocab pairs
    - date_event_field (int): The ID of the date event field
    - person_id_field (int): The ID of the person ID field
    """
    try:
        # Get validated parameters from XCom
        validated_params = pull_validated_params(kwargs, "validate_params_V_concepts")

        scan_report_id = validated_params["scan_report_id"]
        table_id = validated_params["table_id"]
        field_vocab_pairs = validated_params["field_vocab_pairs"]
        date_field_id = validated_params["date_event_field"]
        person_id_field = validated_params["person_id_field"]

        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
            status=StageStatusType.IN_PROGRESS,
            details="Creating mapping rules for V concepts...",
        )

        for pair in field_vocab_pairs:
            sr_field_id = pair["sr_field_id"]

            # Create comprehensive single mapping rule query to handle all rules at once
            mapping_rule_query = f"""
            INSERT INTO mapping_mappingrule (
                created_at, updated_at, omop_field_id, source_field_id, concept_id, scan_report_id, approved
            )
            SELECT 
                NOW(), NOW(), field_id, source_id, sr_concept_id, {scan_report_id}, TRUE
            FROM temp_standard_concepts_{table_id}
            CROSS JOIN LATERAL (
                VALUES 
                    (dest_person_field_id, {person_id_field}),
                    (dest_date_field_id, {date_field_id}),
                    (dest_start_date_field_id, {date_field_id}),
                    (dest_end_date_field_id, {date_field_id}),
                    (source_concept_field_id, {sr_field_id}),
                    (dest_concept_field_id, {sr_field_id}),
                    (source_value_field_id, {sr_field_id}),
                    (value_as_string_field_id, {sr_field_id}),
                    (value_as_number_field_id, {sr_field_id})
            ) AS field_mapping(field_id, source_id)
            WHERE field_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM mapping_mappingrule exited_mapping_rule
                WHERE exited_mapping_rule.omop_field_id = field_mapping.field_id
                AND exited_mapping_rule.source_field_id = field_mapping.source_id
                AND exited_mapping_rule.scan_report_id = {scan_report_id}
            )
            ORDER BY sr_value_id;
            """

            try:
                result = pg_hook.run(mapping_rule_query)
                logging.info(
                    "Successfully created all mapping rules for each standard concept"
                )
                update_job_status(
                    scan_report=scan_report_id,
                    scan_report_table=table_id,
                    stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
                    status=StageStatusType.COMPLETE,
                    details="Successfully created mapping rules for V concepts",
                )
                return result
            except Exception as e:
                logging.error(f"Database error in create_mapping_rules: {str(e)}")
                raise AirflowException(
                    f"Database error in create_mapping_rules: {str(e)}"
                )
    except Exception as e:
        logging.error(f"Error in create_mapping_rules: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
            status=StageStatusType.FAILED,
            details=f"Error when creating mapping rules for V concepts",
        )
        raise AirflowException(f"Error in create_mapping_rules: {str(e)}")

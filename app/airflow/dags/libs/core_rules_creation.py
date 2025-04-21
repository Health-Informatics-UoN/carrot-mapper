from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging
from airflow.exceptions import AirflowException
from libs.utils import extract_params

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def delete_mapping_rules(**kwargs):
    """
    Delete all mapping rules for a given scan report table.
    """
    try:
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")

        delete_query = f"""
        DELETE FROM mapping_mappingrule
        WHERE source_field_id IN (
            SELECT id FROM mapping_scanreportfield
            WHERE scan_report_table_id = {table_id}
        );
        """
        pg_hook.run(delete_query)
    except Exception as e:
        logging.error(f"Error in delete_mapping_rules: {str(e)}")
        raise AirflowException(f"Error in delete_mapping_rules: {str(e)}")


def create_mapping_rules(**kwargs):
    """
    Create mapping rules in the mapping_mappingrule table for each record in temp_standard_concepts.
    Each record can generate multiple mapping rules based on the provided rules criteria.
    """
    try:
        table_id, field_vocab_pairs = extract_params(**kwargs)
        scan_report_id = kwargs.get("dag_run", {}).conf.get("scan_report_id")
        person_id_field = kwargs.get("dag_run", {}).conf.get("person_id_field")
        date_field_id = kwargs.get("dag_run", {}).conf.get("date_event_field")

        if not scan_report_id or not field_vocab_pairs:
            logging.warning(
                "No scan_report_id or field-vocabulary pairs provided in create_concepts_rules"
            )
            raise AirflowException(
                "Either scan_report_id or field-vocabulary pairs are required for creating mapping rules"
            )

        for pair in field_vocab_pairs:
            sr_field_id = pair.get("sr_field_id")

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
                SELECT 1 FROM mapping_mappingrule mr
                WHERE mr.omop_field_id = field_mapping.field_id
                AND mr.source_field_id = field_mapping.source_id
                AND mr.scan_report_id = {scan_report_id}
            )
            ORDER BY sr_value_id;
            """

            try:
                result = pg_hook.run(mapping_rule_query)
                logging.info(
                    "Successfully created all mapping rules for each standard concept"
                )
                return result
            except Exception as e:
                logging.error(f"Database error in create_mapping_rules: {str(e)}")
                raise AirflowException(
                    f"Database error in create_mapping_rules: {str(e)}"
                )
    except Exception as e:
        logging.error(f"Error in create_mapping_rules: {str(e)}")
        raise AirflowException(f"Error in create_mapping_rules: {str(e)}")

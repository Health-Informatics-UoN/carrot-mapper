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


def create_person_rules(**kwargs):
    """
    Create mapping rules in the mapping_mappingrule table for each record in temp_standard_concepts.
    Maps person_id fields to their corresponding destination fields.
    """
    try:
        scan_report_id = kwargs.get("dag_run", {}).conf.get("scan_report_id")
        person_id_field = kwargs.get("dag_run", {}).conf.get("person_id_field")

        if not scan_report_id or not person_id_field:
            logging.warning(
                "Either scan_report_id or person_id_field is missing in create_person_rules"
            )
            raise AirflowException(
                "Either scan_report_id or person_id_field is required for creating mapping rules"
            )

        # Create mapping rules for person ID fields
        mapping_rule_query = f"""
        INSERT INTO temp_mapping_rules (
            created_at,
            updated_at,
            omop_field_id,
            source_field_id,
            concept_id,
            scan_report_id,
            approved
        )
        SELECT
            NOW(),
            NOW(),
            tsc.dest_person_field_id,
            {person_id_field},
            tsc.sr_concept_id,
            {scan_report_id},
            TRUE
        FROM temp_standard_concepts tsc
        WHERE tsc.dest_person_field_id IS NOT NULL;
        """
        try:
            result = pg_hook.run(mapping_rule_query)
            logging.info("Successfully created mapping rules for person ID fields")
            return result
        except Exception as e:
            AirflowException(f"Database error in create_mapping_rules: {str(e)}")
            raise
    except Exception as e:
        AirflowException(f"Error in create_mapping_rules: {str(e)}")
        raise


def create_dates_rules(**kwargs):
    """
    Create mapping rules in the mapping_mappingrule table for date fields.
    Maps date event fields to their corresponding destination date fields.
    """
    try:
        scan_report_id = kwargs.get("dag_run", {}).conf.get("scan_report_id")
        date_event_field = kwargs.get("dag_run", {}).conf.get("date_event_field")

        if not scan_report_id or not date_event_field:
            logging.warning(
                "Either scan_report_id or date_event_field is missing in create_dates_rules"
            )
            raise AirflowException(
                "Either scan_report_id or date_event_field is required for creating mapping rules"
            )

        # Create mapping rules for all date field types in a single query
        date_mapping_query = f"""
        INSERT INTO temp_mapping_rules (
            created_at, updated_at, omop_field_id, source_field_id, concept_id, scan_report_id, approved
        )
        SELECT NOW(), NOW(), date_field, {date_event_field}, tsc.sr_concept_id, {scan_report_id}, TRUE
        FROM temp_standard_concepts tsc
        CROSS JOIN LATERAL (
            VALUES 
                (tsc.dest_date_field_id),
                (tsc.dest_start_date_field_id),
                (tsc.dest_end_date_field_id)
        ) AS fields(date_field)
        WHERE date_field IS NOT NULL;
        """

        try:
            result = pg_hook.run(date_mapping_query)
            logging.info("Successfully created mapping rules for date fields")
            return result
        except Exception as e:
            logging.error(f"Database error in create_dates_rules: {str(e)}")
            raise AirflowException(f"Database error in create_dates_rules: {str(e)}")
    except Exception as e:
        logging.error(f"Error in create_dates_rules: {str(e)}")
        raise AirflowException(f"Error in create_dates_rules: {str(e)}")


def create_concepts_rules(**kwargs):
    """
    Create mapping rules in the mapping_mappingrule table for concept-related fields.
    Maps fields to their corresponding destination concept fields.
    """
    try:
        table_id, field_vocab_pairs = extract_params(**kwargs)
        scan_report_id = kwargs.get("dag_run", {}).conf.get("scan_report_id")

        if not scan_report_id or not field_vocab_pairs:
            logging.warning(
                "No scan_report_id or field-vocabulary pairs provided in create_concepts_rules"
            )
            raise AirflowException(
                "Either scan_report_id or field-vocabulary pairs are required for creating mapping rules"
            )

        for pair in field_vocab_pairs:
            sr_field_id = pair.get("sr_field_id")

            # Create mapping rules for all concept-related field types in a single query
            concepts_mapping_query = f"""
            INSERT INTO temp_mapping_rules (
                created_at, updated_at, omop_field_id, source_field_id, concept_id, scan_report_id, approved
            )
            SELECT NOW(), NOW(), field_id, {sr_field_id}, tsc.sr_concept_id, {scan_report_id}, TRUE
            FROM temp_standard_concepts tsc
            CROSS JOIN LATERAL (
                VALUES 
                    (tsc.source_value_field_id),
                    (tsc.source_concept_field_id),
                    (tsc.dest_concept_field_id),
                    (tsc.value_as_number_field_id),
                    (tsc.value_as_string_field_id)
            ) AS fields(field_id)
            WHERE field_id IS NOT NULL;
            """

            try:
                result = pg_hook.run(concepts_mapping_query)
                logging.info("Successfully created mapping rules for concept fields")
                return result
            except Exception as e:
                logging.error(f"Database error in create_concepts_rules: {str(e)}")
                raise AirflowException(
                    f"Database error in create_concepts_rules: {str(e)}"
                )
    except Exception as e:
        logging.error(f"Error in create_concepts_rules: {str(e)}")
        raise AirflowException(f"Error in create_concepts_rules: {str(e)}")


# TODO: we may use this when we have the source_concept_id in the model SCANREPORTCONCEPT
def create_source_concept_rules(**kwargs):
    """
    Create mapping rules in the mapping_mappingrule table for source concept fields.
    Uses source_concept_id instead of standard_concept_id for the concept mapping.
    """
    try:
        table_id, field_vocab_pairs = extract_params(**kwargs)
        scan_report_id = kwargs.get("dag_run", {}).conf.get("scan_report_id")

        if not field_vocab_pairs:
            logging.error("No field-vocabulary pairs provided")
            raise ValueError("No field-vocabulary pairs provided")

        for pair in field_vocab_pairs:
            sr_field_id = pair.get("sr_field_id")

            if not scan_report_id:
                logging.warning(
                    "No scan_report_id provided in create_source_concept_rules"
                )
                raise AirflowException(
                    "scan_report_id is required for creating mapping rules"
                )

            if not sr_field_id:
                logging.warning(
                    "No sr_field_id provided in create_source_concept_rules"
                )
                raise AirflowException(
                    "sr_field_id is required for creating mapping rules"
                )

            # Create mapping rules for source concept fields using source_concept_id
            source_concept_query = f"""
            INSERT INTO temp_mapping_rules (
                created_at, updated_at, omop_field_id, source_field_id, concept_id, scan_report_id, approved
            )
            SELECT
                NOW(), NOW(), tsc.source_concept_field_id, {sr_field_id}, src.id, {scan_report_id}, TRUE
            FROM temp_standard_concepts tsc
            -- TODO: when we have the source_concept_id in the model SCANREPORTCONCEPT, we have to use it here instead of standard_concept_id
            JOIN mapping_scanreportconcept src ON 
                src.object_id = tsc.sr_value_id AND
                src.source_concept_id = tsc.source_concept_id AND  -- Using source_concept_id here instead of standard_concept_id
                src.content_type_id = 23
            WHERE tsc.source_concept_field_id IS NOT NULL
            AND NOT EXISTS (
                -- Check if the mapping rule already exists
                SELECT 1 FROM mapping_mappingrule mr
                WHERE mr.omop_field_id = tsc.source_concept_field_id
                AND mr.source_field_id = {sr_field_id}
                AND mr.concept_id = src.id
                AND mr.scan_report_id = {scan_report_id}
            );
            """

            try:
                result = pg_hook.run(source_concept_query)
                logging.info(
                    "Successfully created mapping rules for source concept fields"
                )
                return result
            except Exception as e:
                logging.error(
                    f"Database error in create_source_concept_rules: {str(e)}"
                )
                raise AirflowException(
                    f"Database error in create_source_concept_rules: {str(e)}"
                )

    except Exception as e:
        logging.error(f"Error in create_source_concept_rules: {str(e)}")
        raise AirflowException(f"Error in create_source_concept_rules: {str(e)}")


def temp_mapping_rules_table_creation():
    """
    Create the temp_mapping_rules table if it doesn't exist.
    """
    try:
        create_temp_table_query = """
        DROP TABLE IF EXISTS temp_mapping_rules;
        CREATE TABLE IF NOT EXISTS temp_mapping_rules (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            omop_field_id INTEGER,
            source_field_id INTEGER,
            concept_id INTEGER,
            scan_report_id INTEGER,
            approved BOOLEAN
        );
        """
        pg_hook.run(create_temp_table_query)
    except Exception as e:
        logging.error(f"Error in temp_mapping_rules_table_creation: {str(e)}")
        raise AirflowException(f"Error in temp_mapping_rules_table_creation: {str(e)}")


def add_rules_to_temp_table(**kwargs):
    """
    Add all mapping rules created for a scan report to a temporary table called temp_mapping_rules.
    This should be called after all other rule creation functions to ensure all rules are captured.
    """
    try:
        scan_report_id = kwargs.get("dag_run", {}).conf.get("scan_report_id")

        if not scan_report_id:
            logging.warning("No scan_report_id provided in add_rules_to_temp_table")
            raise AirflowException(
                "scan_report_id is required for adding rules to temporary table"
            )

        # # Clear any existing rules for this scan report to avoid duplicates
        # clear_existing_query = f"""
        # DELETE FROM temp_mapping_rules
        # WHERE scan_report_id = {scan_report_id};
        # """

        # Insert mapping rules into temp_mapping_rules
        insert_rules_query = f"""
        INSERT INTO mapping_mappingrule (
            created_at, updated_at, omop_field_id, 
            source_field_id, concept_id, scan_report_id, approved
        )
        SELECT 
            mr.created_at,
            mr.updated_at,
            mr.omop_field_id,
            mr.source_field_id,
            mr.concept_id,
            mr.scan_report_id,
            mr.approved
        FROM temp_mapping_rules mr
        WHERE mr.scan_report_id = {scan_report_id};
        """

        try:

            # Clear existing rules for this scan report
            # pg_hook.run(clear_existing_query)

            # Insert the mapping rules into the temporary table
            pg_hook.run(insert_rules_query)

        except Exception as e:
            logging.error(f"Database error in add_rules_to_temp_table: {str(e)}")
            raise AirflowException(
                f"Database error in add_rules_to_temp_table: {str(e)}"
            )
    except Exception as e:
        logging.error(f"Error in add_rules_to_temp_table: {str(e)}")
        raise AirflowException(f"Error in add_rules_to_temp_table: {str(e)}")

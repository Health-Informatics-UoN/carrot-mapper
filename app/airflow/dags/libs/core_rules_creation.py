from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging
from airflow.exceptions import AirflowException
from libs.utils import extract_params

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


# TODO: to shorten the Query,create a column standard_concept_id_id (get from the table SR_concepts) in the table temp_standard_concepts, when creating standard concepts
# TODO: do we need to check AND NOT EXISTS?
# TODO: how to prevent someone using the temp_standard_concepts table from other's dag_run?
# TODO: do we need to delete all of the mapping rules before creating/updating new ones? - we have to delete everything becasue of the DEATH table, right?
def create_person_rules(**kwargs):
    """
    Create mapping rules in the mapping_mappingrule table for each record in temp_standard_concepts.
    Maps person_id fields to their corresponding destination fields.
    """
    try:
        scan_report_id = kwargs.get("dag_run", {}).conf.get("scan_report_id")
        person_id_field = kwargs.get("dag_run", {}).conf.get("person_id_field")

        if not scan_report_id:
            logging.warning("No scan_report_id provided in create_mapping_rules")
            raise AirflowException(
                "scan_report_id is required for creating mapping rules"
            )

        if not person_id_field:
            logging.warning("No person_id_field provided in create_mapping_rules")
            raise AirflowException(
                "person_id_field is required for creating mapping rules"
            )

        # Create mapping rules for person ID fields
        mapping_rule_query = f"""
        INSERT INTO mapping_mappingrule (
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
            src.id,
            {scan_report_id},
            TRUE
        FROM temp_standard_concepts tsc
        JOIN mapping_scanreportconcept src ON 
            src.object_id = tsc.sr_value_id AND
            src.concept_id = tsc.standard_concept_id AND
            src.content_type_id = 23  -- content_type_id for scanreportvalue
        WHERE tsc.dest_person_field_id IS NOT NULL
        AND NOT EXISTS (
            -- Check if the mapping rule already exists
            SELECT 1 FROM mapping_mappingrule mr
            WHERE mr.omop_field_id = tsc.dest_person_field_id
            AND mr.source_field_id = {person_id_field}
            AND mr.concept_id = src.id
            AND mr.scan_report_id = {scan_report_id}
        );
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

        if not scan_report_id:
            logging.warning("No scan_report_id provided in create_dates_rules")
            raise AirflowException(
                "scan_report_id is required for creating mapping rules"
            )

        if not date_event_field:
            logging.warning("No date_event_field provided in create_dates_rules")
            raise AirflowException(
                "date_event_field is required for creating mapping rules"
            )

        # Create mapping rules for all date field types in a single query
        date_mapping_query = f"""
        INSERT INTO mapping_mappingrule (
            created_at, updated_at, omop_field_id, source_field_id, concept_id, scan_report_id, approved
        )
        -- Single date fields
        SELECT NOW(), NOW(), date_field_id, {date_event_field}, concept_id, {scan_report_id}, TRUE
        FROM (
            SELECT 
                tsc.dest_date_field_id AS date_field_id,
                src.id AS concept_id
            FROM temp_standard_concepts tsc
            JOIN mapping_scanreportconcept src ON 
                src.object_id = tsc.sr_value_id AND
                src.concept_id = tsc.standard_concept_id AND
                src.content_type_id = 23
            WHERE tsc.dest_date_field_id IS NOT NULL
            
            UNION ALL
            
            -- Start date fields
            SELECT 
                tsc.dest_start_date_field_id AS date_field_id,
                src.id AS concept_id
            FROM temp_standard_concepts tsc
            JOIN mapping_scanreportconcept src ON 
                src.object_id = tsc.sr_value_id AND
                src.concept_id = tsc.standard_concept_id AND
                src.content_type_id = 23
            WHERE tsc.dest_start_date_field_id IS NOT NULL
            
            UNION ALL
            
            -- End date fields
            SELECT 
                tsc.dest_end_date_field_id AS date_field_id,
                src.id AS concept_id
            FROM temp_standard_concepts tsc
            JOIN mapping_scanreportconcept src ON 
                src.object_id = tsc.sr_value_id AND
                src.concept_id = tsc.standard_concept_id AND
                src.content_type_id = 23
            WHERE tsc.dest_end_date_field_id IS NOT NULL
        ) AS date_fields
        WHERE NOT EXISTS (
            -- Check if the mapping rule already exists
            SELECT 1 FROM mapping_mappingrule mr
            WHERE mr.omop_field_id = date_fields.date_field_id
            AND mr.source_field_id = {date_event_field}
            AND mr.concept_id = date_fields.concept_id
            AND mr.scan_report_id = {scan_report_id}
        );
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

        if not field_vocab_pairs:
            logging.error("No field-vocabulary pairs provided")
            raise ValueError("No field-vocabulary pairs provided")

        for pair in field_vocab_pairs:
            sr_field_id = pair.get("sr_field_id")

            if not scan_report_id:
                logging.warning("No scan_report_id provided in create_concepts_rules")
                raise AirflowException(
                    "scan_report_id is required for creating mapping rules"
                )

            if not sr_field_id:
                logging.warning("No sr_field_id provided in create_concepts_rules")
                raise AirflowException(
                    "sr_field_id is required for creating mapping rules"
                )

            # Create mapping rules for all concept-related field types in a single query
            concepts_mapping_query = f"""
            INSERT INTO mapping_mappingrule (
                created_at, updated_at, omop_field_id, source_field_id, concept_id, scan_report_id, approved
            )
            SELECT NOW(), NOW(), field_id, {sr_field_id}, concept_id, {scan_report_id}, TRUE
            FROM (
                -- Source value fields
                SELECT 
                    tsc.source_value_field_id AS field_id,
                    src.id AS concept_id
                FROM temp_standard_concepts tsc
                JOIN mapping_scanreportconcept src ON 
                    src.object_id = tsc.sr_value_id AND
                    src.concept_id = tsc.standard_concept_id AND
                    src.content_type_id = 23
                WHERE tsc.source_value_field_id IS NOT NULL

                UNION ALL
                
                -- Source concept fields
                -- TODO: when we have the source_concept_id in the model SCANREPORTCONCEPT, we have to use it here instead of standard_concept_id
                SELECT 
                    tsc.source_concept_field_id AS field_id,
                    src.id AS concept_id
                FROM temp_standard_concepts tsc
                JOIN mapping_scanreportconcept src ON 
                    src.object_id = tsc.sr_value_id AND
                    src.concept_id = tsc.standard_concept_id AND
                    src.content_type_id = 23
                WHERE tsc.source_concept_field_id IS NOT NULL

                UNION ALL
                
                -- Destination concept fields
                SELECT 
                    tsc.dest_concept_field_id AS field_id,
                    src.id AS concept_id
                FROM temp_standard_concepts tsc
                JOIN mapping_scanreportconcept src ON 
                    src.object_id = tsc.sr_value_id AND
                    src.concept_id = tsc.standard_concept_id AND
                    src.content_type_id = 23
                WHERE tsc.dest_concept_field_id IS NOT NULL
                
                UNION ALL
                
                -- Value as number fields
                SELECT 
                    tsc.value_as_number_field_id AS field_id,
                    src.id AS concept_id
                FROM temp_standard_concepts tsc
                JOIN mapping_scanreportconcept src ON 
                    src.object_id = tsc.sr_value_id AND
                    src.concept_id = tsc.standard_concept_id AND
                    src.content_type_id = 23
                WHERE tsc.value_as_number_field_id IS NOT NULL
                
                UNION ALL
                
                -- Value as string fields
                SELECT 
                    tsc.value_as_string_field_id AS field_id,
                    src.id AS concept_id
                FROM temp_standard_concepts tsc
                JOIN mapping_scanreportconcept src ON 
                    src.object_id = tsc.sr_value_id AND
                    src.concept_id = tsc.standard_concept_id AND
                    src.content_type_id = 23
                WHERE tsc.value_as_string_field_id IS NOT NULL
            ) AS concept_fields
            WHERE NOT EXISTS (
                -- Check if the mapping rule already exists
                SELECT 1 FROM mapping_mappingrule mr
                WHERE mr.omop_field_id = concept_fields.field_id
                AND mr.source_field_id = {sr_field_id}
                AND mr.concept_id = concept_fields.concept_id
                AND mr.scan_report_id = {scan_report_id}
            );
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
            INSERT INTO mapping_mappingrule (
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

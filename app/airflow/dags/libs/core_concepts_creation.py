from libs.utils import extract_params
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def find_standard_concepts(**kwargs):
    """
    Find standard concepts for field-vocabulary pairs.
    Creates a temporary table containing mappings between source and standard concepts.
    """
    try:
        table_id, field_vocab_pairs = extract_params(**kwargs)

        if not field_vocab_pairs:
            logging.error("No field-vocabulary pairs provided")
            raise ValueError("No field-vocabulary pairs provided")

        # Create the temporary table once, outside the loop, with all the columns needed
        create_table_query = f"""
        DROP TABLE IF EXISTS temp_standard_concepts_{table_id};
        CREATE TABLE temp_standard_concepts_{table_id} (
            sr_value_id INTEGER,
            source_concept_id INTEGER,
            standard_concept_id INTEGER,
            sr_concept_id INTEGER,
            dest_table_id INTEGER,
            dest_person_field_id INTEGER,
            dest_date_field_id INTEGER,
            dest_start_date_field_id INTEGER,
            dest_end_date_field_id INTEGER,
            source_concept_field_id INTEGER,
            source_value_field_id INTEGER,
            dest_concept_field_id INTEGER,
            value_as_number_field_id INTEGER,
            value_as_string_field_id INTEGER
        );
        """
        try:
            pg_hook.run(create_table_query)
            logging.info(
                f"Successfully created temp_standard_concepts_{table_id} table"
            )
        except Exception as e:
            logging.error(
                f"Failed to create temp_standard_concepts_{table_id} table: {str(e)}"
            )
            raise

        # Process each field-vocabulary pair
        for pair in field_vocab_pairs:
            sr_field_id = pair.get("sr_field_id")
            vocabulary_id = pair.get("vocabulary_id")

            if not sr_field_id or not vocabulary_id:
                raise ValueError(
                    "Invalid field_vocab_pair: requires sr_field_id and vocabulary_id"
                )

            # Insert data for each field-vocabulary pair
            insert_concepts_query = f"""
            INSERT INTO temp_standard_concepts_{table_id} (sr_value_id, source_concept_id, standard_concept_id)
            SELECT
                srv.id AS sr_value_id,
                c1.concept_id AS source_concept_id,
                c2.concept_id AS standard_concept_id
            FROM mapping_scanreportvalue srv
            JOIN omop.concept c1 ON
                c1.concept_code = srv.value AND
                c1.vocabulary_id = '{vocabulary_id}'
            JOIN omop.concept_relationship cr ON
                cr.concept_id_1 = c1.concept_id AND
                cr.relationship_id = 'Maps to'
            JOIN omop.concept c2 ON
                c2.concept_id = cr.concept_id_2 AND
                c2.standard_concept = 'S'
            WHERE srv.scan_report_field_id = {sr_field_id};
            """
            try:
                pg_hook.run(insert_concepts_query)
                logging.info(
                    f"Successfully inserted standard concepts for field ID {sr_field_id}"
                )
            except Exception as e:
                logging.error(
                    f"Failed to insert standard concepts for field ID {sr_field_id}: {str(e)}"
                )
                raise
    except Exception as e:
        logging.error(f"Error in find_standard_concepts: {str(e)}")
        raise


def create_standard_concepts(**kwargs):
    """
    Create standard concepts for field values in the mapping_scanreportconcept table.
    Only inserts concepts that don't already exist.
    """
    try:
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")

        if not table_id:
            logging.warning("No table_id provided in create_standard_concepts")

        create_concept_query = f"""
            -- Insert standard concepts for field values (only if they don't already exist)
            INSERT INTO mapping_scanreportconcept (
                created_at,
                updated_at,
                object_id,
                creation_type,
                concept_id,
                content_type_id
            )
            SELECT
                NOW(),
                NOW(),
                tsc.sr_value_id,
                'V', -- Creation type: Built from Vocab dict
                tsc.standard_concept_id,
                23 -- content_type_id for scanreportvalue
            FROM temp_standard_concepts_{table_id} tsc
            WHERE NOT EXISTS (
                -- Check if the concept already exists
                SELECT 1 FROM mapping_scanreportconcept
                WHERE object_id = tsc.sr_value_id
                AND concept_id = tsc.standard_concept_id
                AND content_type_id = 23
            );
            """
        try:
            result = pg_hook.run(create_concept_query)
            logging.info("Successfully created standard concepts")
            return result
        except Exception as e:
            logging.error(f"Database error in create_standard_concepts: {str(e)}")
            raise
    except Exception as e:
        logging.error(f"Error in create_standard_concepts: {str(e)}")
        raise


def find_sr_concept_id(**kwargs):
    """
    Update temp_standard_concepts table with sr_concept_id column
    containing the IDs of standard concepts added to mapping_scanreportconcept.
    This will help the next steps to be shorter.
    """
    try:
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")

        if not table_id:
            logging.warning("No table_id provided in find_sr_concept_id")

        update_query = f"""        
        -- Update sr_concept_id with the mapping_scanreportconcept ID
        UPDATE temp_standard_concepts_{table_id} tsc
        SET sr_concept_id = src.id
        FROM mapping_scanreportconcept src
        WHERE src.object_id = tsc.sr_value_id
        AND src.concept_id = tsc.standard_concept_id
        AND src.content_type_id = 23;
        """

        try:
            pg_hook.run(update_query)
            logging.info(
                f"Successfully added sr_concept_id to temp_standard_concepts_{table_id} table"
            )
        except Exception as e:
            logging.error(f"Database error in find_sr_concept_id: {str(e)}")
            raise
    except Exception as e:
        logging.error(f"Error in find_sr_concept_id: {str(e)}")
        raise

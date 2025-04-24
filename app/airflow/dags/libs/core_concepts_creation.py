from libs.utils import (
    process_field_vocab_pairs,
    update_job_status,
    JobStageType,
    StageStatusType,
)
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def find_standard_concepts(**kwargs):
    """
    Maps source field values to standard OMOP concepts based on field-vocabulary pairs.

    Creates a temporary table to store mapping information between source values and
    standard concepts. For each field-vocabulary pair provided, finds corresponding
    standard concepts in the OMOP vocabulary and inserts them into the temporary table.

    """
    try:
        scan_report_id = kwargs.get("dag_run", {}).conf.get("scan_report_id")
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")
        field_vocab_pairs = process_field_vocab_pairs(
            kwargs.get("dag_run", {}).conf.get("field_vocab_pairs")
        )

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

            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
                status=StageStatusType.IN_PROGRESS,
                details=f"Finding standard concepts for field ID {sr_field_id} with vocabulary ID {vocabulary_id}",
            )
            # Insert data for each field-vocabulary pair
            find_standard_concepts_query = f"""
            INSERT INTO temp_standard_concepts_{table_id} (sr_value_id, source_concept_id, standard_concept_id)
            SELECT
                sr_value.id AS sr_value_id,
                src_concept.concept_id AS source_concept_id,
                std_concept.concept_id AS standard_concept_id
            FROM mapping_scanreportvalue sr_value
            JOIN omop.concept src_concept ON
                src_concept.concept_code = sr_value.value AND
                src_concept.vocabulary_id = '{vocabulary_id}'
            JOIN omop.concept_relationship concept_relationship ON
                concept_relationship.concept_id_1 = src_concept.concept_id AND
                concept_relationship.relationship_id = 'Maps to'
            JOIN omop.concept std_concept ON
                std_concept.concept_id = concept_relationship.concept_id_2 AND
                std_concept.standard_concept = 'S'
            WHERE sr_value.scan_report_field_id = {sr_field_id};
            """
            try:
                pg_hook.run(find_standard_concepts_query)
                logging.info(
                    f"Successfully inserted standard concepts for field ID {sr_field_id}"
                )
            except Exception as e:
                logging.error(
                    f"Failed to insert standard concepts for field ID {sr_field_id}: {str(e)}"
                )
                update_job_status(
                    scan_report=scan_report_id,
                    scan_report_table=table_id,
                    stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
                    status=StageStatusType.FAILED,
                    details=f"Error in find_standard_concepts_query: {str(e)}",
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
        scan_report_id = kwargs.get("dag_run", {}).conf.get("scan_report_id")
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")

        if not table_id:
            logging.warning("No table_id provided in create_standard_concepts")
        # TODO: when source_concept_id is added to the model SCANREPORTCONCEPT, we need to update the query belowto solve the issue #1006
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
                temp_std_concepts.sr_value_id,
                'V',           -- Creation type: Built from Vocab dict
                temp_std_concepts.standard_concept_id,
                23             -- content_type_id for scanreportvalue
            FROM temp_standard_concepts_{table_id} temp_std_concepts
            WHERE NOT EXISTS (
                -- Check if the concept already exists
                SELECT 1 FROM mapping_scanreportconcept
                WHERE object_id = temp_std_concepts.sr_value_id
                AND concept_id = temp_std_concepts.standard_concept_id
                AND content_type_id = 23
            );
            """
        try:
            pg_hook.run(create_concept_query)
            logging.info("Successfully created standard concepts")
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
                status=StageStatusType.COMPLETE,
                details="Successfully created standard concepts",
            )
        except Exception as e:
            logging.error(f"Database error in create_standard_concepts: {str(e)}")
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
                status=StageStatusType.FAILED,
                details=f"Error in create_standard_concepts: {str(e)}",
            )
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
        UPDATE temp_standard_concepts_{table_id} temp_std_concepts
        SET sr_concept_id = sr_concept.id
        FROM mapping_scanreportconcept sr_concept
        WHERE sr_concept.object_id = temp_std_concepts.sr_value_id
        AND sr_concept.concept_id = temp_std_concepts.standard_concept_id
        AND sr_concept.content_type_id = 23;
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

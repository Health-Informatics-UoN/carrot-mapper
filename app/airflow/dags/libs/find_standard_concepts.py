from libs.utils import (
    update_job_status,
    JobStageType,
    StageStatusType,
    pull_validated_params,
)
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def find_standard_concepts(**kwargs) -> None:
    """
    Maps source field values to standard OMOP concepts based on field-vocabulary pairs.

    Creates a temporary table to store mapping information between source values and
    standard concepts. For each field-vocabulary pair provided, finds corresponding
    standard concepts in the OMOP vocabulary and inserts them into the temporary table.
    Validated params needed are:
    - scan_report_id (int): The ID of the scan report to process
    - table_id (int): The ID of the scan report table to process
    - field_vocab_pairs (list): List of dictionaries containing field-vocab pairs
        For example:
        "field_vocab_pairs": [
            {
                "sr_field_id": "437",
                "field_data_type": "VARCHAR",
                "vocabulary_id": "ICD10"
            }
        ]
    """

    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params")

    scan_report_id = validated_params["scan_report_id"]
    table_id = validated_params["table_id"]
    field_vocab_pairs = validated_params["field_vocab_pairs"]
    # Create the temporary table once, outside the loop, with all the columns needed
    create_table_query = f"""
    DROP TABLE IF EXISTS temp_standard_concepts_{table_id};
    CREATE TABLE temp_standard_concepts_{table_id} (
        sr_value_id INTEGER,
        source_concept_id INTEGER,
        standard_concept_id INTEGER
    );
    """
    try:
        pg_hook.run(create_table_query)
        logging.info(f"Successfully created temp_standard_concepts_{table_id} table")
    except Exception as e:
        logging.error(
            f"Failed to create temp_standard_concepts_{table_id} table: {str(e)}"
        )
        raise

    # Process each field-vocabulary pair
    for pair in field_vocab_pairs:
        sr_field_id = pair["sr_field_id"]
        vocabulary_id = pair["vocabulary_id"]

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
        FROM mapping_scanreportvalue AS sr_value
        JOIN omop.concept AS src_concept ON
            src_concept.concept_code = sr_value.value AND
            src_concept.vocabulary_id = '{vocabulary_id}'
        JOIN omop.concept_relationship AS concept_relationship ON
            concept_relationship.concept_id_1 = src_concept.concept_id AND
            concept_relationship.relationship_id = 'Maps to'
        JOIN omop.concept AS std_concept ON
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
                details=f"Error in finding standard concepts for field ID {sr_field_id}",
            )
            raise


def create_standard_concepts(**kwargs) -> None:
    """
    Create standard concepts for field values in the mapping_scanreportconcept table.
    Only inserts concepts that don't already exist.
    Validated params needed are:
    - scan_report_id (int): The ID of the scan report to process
    - table_id (int): The ID of the scan report table to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params")

    scan_report_id = validated_params["scan_report_id"]
    table_id = validated_params["table_id"]

    # TODO: when source_concept_id is added to the model SCANREPORTCONCEPT, we need to update the query belowto solve the issue #1006
    create_concept_query = f"""
        -- Insert standard concepts for field values (only if they don't already exist)
        INSERT INTO mapping_scanreportconcept (
            created_at,
            updated_at,
            object_id,
            creation_type,
            -- TODO: when we can distinguish between source and standard concepts, we can add value to this column
            -- source_concept_id,
            concept_id,
            content_type_id
        )
        SELECT
            NOW(),
            NOW(),
            temp_std_concepts.sr_value_id,
            'V',           -- Creation type: Built from Vocab dict
            -- TODO: when we can distinguish between source and standard concepts, we can add value to this column
            -- temp_std_concepts.source_concept_id,
            temp_std_concepts.standard_concept_id,
            23             -- content_type_id for scanreportvalue
        FROM temp_standard_concepts_{table_id} AS temp_std_concepts
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
            status=StageStatusType.IN_PROGRESS,
            details="Standard concepts created",
        )
    except Exception as e:
        logging.error(f"Database error in create_standard_concepts: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
            status=StageStatusType.FAILED,
            details=f"Error when creating standard concepts",
        )

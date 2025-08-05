from libs.utils import (
    update_job_status,
    JobStageType,
    StageStatusType,
    pull_validated_params,
)
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging
from libs.queries import (
    find_dest_table_and_person_field_id_query,
    find_dates_fields_query,
    find_concept_fields_query,
)
from libs.settings import AIRFLOW_DAGRUN_TIMEOUT

# PostgreSQL connection hook
pg_hook = PostgresHook(
    postgres_conn_id="postgres_db_conn",
    options=f"-c statement_timeout={float(AIRFLOW_DAGRUN_TIMEOUT) * 60 * 1000}ms",
)


def find_dest_table_and_person_field_id(**kwargs) -> None:
    """
    Add destination table IDs and person field IDs to the temporary concepts table.
    This function updates the temporary standard concepts table with appropriate
    destination table IDs and person field IDs based on OMOP concept domains. It performs
    two main SQL operations:

    1. Maps concept domains to appropriate OMOP tables (e.g., 'Race'/'Gender'/'Ethnicity'
       to 'person', 'Condition' to 'condition_occurrence', etc.) and sets the dest_table_id
       in the temporary concepts table.
    2. Adds the person_id field reference to each record by finding the corresponding field
       in the mapping_omopfield table.

    Validated params needed are:
    - scan_report_id (int): The ID of the scan report to process
    - table_id (int): The ID of the scan report table to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")

    table_id = validated_params["table_id"]
    scan_report_id = validated_params["scan_report_id"]

    update_job_status(
        scan_report=scan_report_id,
        scan_report_table=table_id,
        stage=JobStageType.GENERATE_RULES,
        status=StageStatusType.IN_PROGRESS,
        details="Finding destination table and destination OMOP field IDs...",
    )

    try:
        pg_hook.run(
            find_dest_table_and_person_field_id_query,
            parameters={"table_id": table_id},
        )
        logging.info("Successfully added destination table and person field IDs")
    except Exception as e:
        logging.error(
            f"Database error in find_dest_table_and_person_field_id: {str(e)}"
        )
        raise


def find_date_fields(**kwargs) -> None:
    """
    Add date field IDs to the temporary concepts table based on the date field mapper.

    This function updates the temporary standard concepts table with appropriate date-related
    field IDs from the OMOP CDM model. It handles three types of date fields:

    1. dest_date_field_id: Single datetime fields for tables with one date (person, measurement,
       observation, procedure_occurrence, specimen)
    2. dest_start_date_field_id: Start datetime fields for tables with date ranges
       (condition_occurrence, drug_exposure, device_exposure)
    3. dest_end_date_field_id: End datetime fields for tables with date ranges
       (condition_occurrence, drug_exposure, device_exposure)

    The function uses a single SQL query with subqueries to efficiently map the correct
    datetime fields for each table based on OMOP CDM conventions.

    Validated params needed are:
    - table_id (int): The ID of the scan report table to process
    """

    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")
    table_id = validated_params["table_id"]

    try:
        pg_hook.run(find_dates_fields_query, parameters={"table_id": table_id})
        logging.info("Successfully added date field IDs based on the date field mapper")
    except Exception as e:
        logging.error(f"Database error in find_date_fields: {str(e)}")
        raise


def find_concept_fields(**kwargs) -> None:
    """
    Add concept-related field IDs to the temporary concepts table.
    Includes source concept, source value, and destination concept fields.
    Uses domain-specific field patterns with strict table mapping.

    Validated params needed are:
    - table_id (int): The ID of the scan report table to process
    """

    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")

    table_id = validated_params["table_id"]

    try:
        pg_hook.run(find_concept_fields_query, parameters={"table_id": table_id})
        logging.info("Successfully added concept field IDs")
    except Exception as e:
        logging.error(f"Database error in find_concept_fields: {str(e)}")
        raise


def find_additional_fields(**kwargs) -> None:
    """
    Add additional field IDs to the temporary concepts table based on data types.
    Handles measurement domain and observation domain concepts using the
    source_field_data_type from the temp_existing_concepts table.

    Validated params needed are:
    - table_id (int): The ID of the scan report table to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")
    table_id = validated_params["table_id"]

    # Always add value_as_number to Measurement domain concepts, but ONLY if they're in the measurement table
    measurement_query = """
    -- Update value_as_number_field_id for measurement domain concepts ONLY
    UPDATE temp_existing_concepts_%(table_id)s temp_existing_concepts
    SET value_as_number_field_id = omop_field.id
    FROM mapping_omopfield omop_field, omop.concept target_concept, mapping_omoptable omop_table
    WHERE 
        target_concept.concept_id = COALESCE(temp_existing_concepts.standard_concept_id, temp_existing_concepts.source_concept_id) AND
        target_concept.domain_id = 'Measurement' AND
        omop_field.table_id = temp_existing_concepts.dest_table_id AND
        omop_field.field = 'value_as_number' AND
        omop_table.id = temp_existing_concepts.dest_table_id AND
        omop_table.table = 'measurement';
    """

    try:
        pg_hook.run(measurement_query, parameters={"table_id": table_id})
        logging.info(
            "Successfully added value_as_number for Measurement domain concepts"
        )
    except Exception as e:
        logging.error(f"Database error in measurement_query: {str(e)}")
        raise

    # Add value_as_number to Observation domain concepts with numeric data types
    observation_number_query = """
    -- Update value_as_number_field_id for Observation domain concepts with numeric data types
    UPDATE temp_existing_concepts_%(table_id)s temp_existing_concepts
    SET value_as_number_field_id = omop_field.id
    FROM mapping_omopfield omop_field, omop.concept target_concept, mapping_omoptable omop_table
    WHERE 
        target_concept.concept_id = COALESCE(temp_existing_concepts.standard_concept_id, temp_existing_concepts.source_concept_id) AND
        target_concept.domain_id = 'Observation' AND
        omop_field.table_id = temp_existing_concepts.dest_table_id AND
        omop_field.field = 'value_as_number' AND
        omop_table.id = temp_existing_concepts.dest_table_id AND
        omop_table.table = 'observation' AND
        temp_existing_concepts.source_field_data_type = 'numeric';
    """

    try:
        pg_hook.run(observation_number_query, parameters={"table_id": table_id})
        logging.info(
            "Successfully added value_as_number for Observation domain concepts"
        )
    except Exception as e:
        logging.error(f"Database error in observation_number_query: {str(e)}")
        raise

    # Add value_as_string to Observation domain concepts with string data types
    observation_string_query = """
    -- Update value_as_string_field_id for Observation domain concepts with string data types
    UPDATE temp_existing_concepts_%(table_id)s temp_existing_concepts
    SET value_as_string_field_id = omop_field.id
    FROM mapping_omopfield omop_field, omop.concept target_concept, mapping_omoptable omop_table
    WHERE 
        target_concept.concept_id = COALESCE(temp_existing_concepts.standard_concept_id, temp_existing_concepts.source_concept_id) AND
        target_concept.domain_id = 'Observation' AND
        omop_field.table_id = temp_existing_concepts.dest_table_id AND
        omop_field.field = 'value_as_string' AND
        omop_table.id = temp_existing_concepts.dest_table_id AND
        omop_table.table = 'observation' AND
        temp_existing_concepts.source_field_data_type = 'string';
    """

    try:
        pg_hook.run(observation_string_query, parameters={"table_id": table_id})
        logging.info(
            "Successfully added value_as_string for Observation domain concepts"
        )
    except Exception as e:
        logging.error(f"Database error in observation_string_query: {str(e)}")
        raise

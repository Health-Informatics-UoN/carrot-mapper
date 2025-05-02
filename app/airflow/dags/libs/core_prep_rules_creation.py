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
    validated_params = pull_validated_params(kwargs, "validate_params")

    table_id = validated_params["table_id"]
    scan_report_id = validated_params["scan_report_id"]

    update_job_status(
        scan_report=scan_report_id,
        scan_report_table=table_id,
        stage=JobStageType.REUSE_CONCEPTS,
        status=StageStatusType.IN_PROGRESS,
        details="Finding destination table and destination OMOP field IDs...",
    )
    core_query = f"""
    -- Update destination table ID
    UPDATE temp_existing_concepts_{table_id} temp_existing_concepts
    SET dest_table_id = omop_table.id
    -- Target concept can be source or standard concept from the temp_existing_concepts table
    FROM omop.concept AS target_concept
    LEFT JOIN mapping_omoptable AS omop_table ON
        CASE target_concept.domain_id
            WHEN 'Race' THEN 'person'
            WHEN 'Gender' THEN 'person'
            WHEN 'Ethnicity' THEN 'person'
            WHEN 'Observation' THEN 'observation'
            WHEN 'Condition' THEN 'condition_occurrence'
            WHEN 'Device' THEN 'device_exposure'
            WHEN 'Measurement' THEN 'measurement'
            WHEN 'Drug' THEN 'drug_exposure'
            WHEN 'Procedure' THEN 'procedure_occurrence'
            WHEN 'Specimen' THEN 'specimen'
            ELSE LOWER(target_concept.domain_id)
        END = omop_table.table
    -- Because concepts for reusing may or maynot have the standard_concept_id. And we prefer to use the standard_concept_id, if it exists.
    WHERE target_concept.concept_id = COALESCE(temp_existing_concepts.standard_concept_id, temp_existing_concepts.source_concept_id);
    
    -- Update person field ID
    UPDATE temp_existing_concepts_{table_id} temp_existing_concepts
    SET dest_person_field_id = omop_field.id
    FROM mapping_omopfield omop_field
    WHERE omop_field.table_id = temp_existing_concepts.dest_table_id
    AND omop_field.field = 'person_id';
    """
    try:
        pg_hook.run(core_query)
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
    validated_params = pull_validated_params(kwargs, "validate_params")

    table_id = validated_params["table_id"]

    # Optimized SQL with better structure and reduced redundancy
    dates_query = f"""
    -- Single consolidated update using CASE expressions for better performance
    UPDATE temp_existing_concepts_{table_id} temp_existing_concepts
    SET 
        dest_date_field_id = (
            SELECT omop_field.id
            FROM mapping_omopfield AS omop_field
            JOIN mapping_omoptable AS omop_table ON omop_table.id = omop_field.table_id
            WHERE omop_field.table_id = temp_existing_concepts.dest_table_id
            AND (
                (omop_table.table = 'person' AND omop_field.field = 'birth_datetime') OR
                (omop_table.table = 'measurement' AND omop_field.field = 'measurement_datetime') OR
                (omop_table.table = 'observation' AND omop_field.field = 'observation_datetime') OR
                (omop_table.table = 'procedure_occurrence' AND omop_field.field = 'procedure_datetime') OR
                (omop_table.table = 'specimen' AND omop_field.field = 'specimen_datetime')
            )
            LIMIT 1
        ),
        
        dest_start_date_field_id = (
            SELECT omop_field.id
            FROM mapping_omopfield AS omop_field
            JOIN mapping_omoptable AS omop_table ON omop_table.id = omop_field.table_id
            WHERE omop_field.table_id = temp_existing_concepts.dest_table_id
            AND (
                (omop_table.table = 'condition_occurrence' AND omop_field.field = 'condition_start_datetime') OR
                (omop_table.table = 'drug_exposure' AND omop_field.field = 'drug_exposure_start_datetime') OR
                (omop_table.table = 'device_exposure' AND omop_field.field = 'device_exposure_start_datetime')
            )
            LIMIT 1
        ),
        
        dest_end_date_field_id = (
            SELECT omop_field.id
            FROM mapping_omopfield AS omop_field
            JOIN mapping_omoptable AS omop_table ON omop_table.id = omop_field.table_id
            WHERE omop_field.table_id = temp_existing_concepts.dest_table_id
            AND (
                (omop_table.table = 'condition_occurrence' AND omop_field.field = 'condition_end_datetime') OR
                (omop_table.table = 'drug_exposure' AND omop_field.field = 'drug_exposure_end_datetime') OR
                (omop_table.table = 'device_exposure' AND omop_field.field = 'device_exposure_end_datetime')
            )
            LIMIT 1
        );
    """

    try:
        pg_hook.run(dates_query)
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
    validated_params = pull_validated_params(kwargs, "validate_params")

    table_id = validated_params["table_id"]

    # Create a staging table with computed field values
    stage_query = f"""
    -- Create a staging table with the correct field IDs for each record
    CREATE TABLE temp_concept_fields_staging_{table_id} AS
    SELECT 
        temp_existing_concepts.object_id,
        target_concept.domain_id,
        target_concept.concept_id AS concept_id,
        -- Use domain-specific source_concept_field_id
        (SELECT omop_field.id 
        FROM mapping_omopfield AS omop_field 
        WHERE omop_field.table_id = temp_existing_concepts.dest_table_id 
        AND omop_field.field = LOWER(target_concept.domain_id) || '_source_concept_id'
        LIMIT 1) AS source_concept_field_id,

        -- Use domain-specific source_value_field_id
        (SELECT omop_field.id 
        FROM mapping_omopfield AS omop_field 
        WHERE omop_field.table_id = temp_existing_concepts.dest_table_id 
        AND omop_field.field = LOWER(target_concept.domain_id) || '_source_value'
        LIMIT 1) AS source_value_field_id,

        -- Use domain-specific dest_concept_field_id
        (SELECT omop_field.id 
        FROM mapping_omopfield AS omop_field 
        WHERE omop_field.table_id = temp_existing_concepts.dest_table_id 
        AND omop_field.field = LOWER(target_concept.domain_id) || '_concept_id'
        LIMIT 1) AS dest_concept_field_id

    FROM temp_existing_concepts_{table_id} temp_existing_concepts
    JOIN omop.concept AS target_concept ON target_concept.concept_id = COALESCE(temp_existing_concepts.standard_concept_id, temp_existing_concepts.source_concept_id);
    
    -- Then update the main table from the staging table
    UPDATE temp_existing_concepts_{table_id} temp_existing_concepts
    SET 
        omop_source_concept_field_id = temp_staging_table.source_concept_field_id,
        omop_source_value_field_id = temp_staging_table.source_value_field_id,
        dest_concept_field_id = temp_staging_table.dest_concept_field_id
    FROM temp_concept_fields_staging_{table_id} temp_staging_table
    WHERE temp_staging_table.object_id = temp_existing_concepts.object_id
    AND temp_staging_table.concept_id = COALESCE(temp_existing_concepts.standard_concept_id, temp_existing_concepts.source_concept_id);
    
    -- Clean up
    DROP TABLE IF EXISTS temp_concept_fields_staging_{table_id};
    """

    try:
        pg_hook.run(stage_query)
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
    validated_params = pull_validated_params(kwargs, "validate_params")
    table_id = validated_params["table_id"]

    # Always add value_as_number to Measurement domain concepts, but ONLY if they're in the measurement table
    measurement_query = f"""
    -- Update value_as_number_field_id for measurement domain concepts ONLY
    UPDATE temp_existing_concepts_{table_id} temp_existing_concepts
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
        pg_hook.run(measurement_query)
        logging.info(
            "Successfully added value_as_number for Measurement domain concepts"
        )
    except Exception as e:
        logging.error(f"Database error in measurement_query: {str(e)}")
        raise

    # Add value_as_number to Observation domain concepts with numeric data types
    observation_number_query = f"""
    -- Update value_as_number_field_id for Observation domain concepts with numeric data types
    UPDATE temp_existing_concepts_{table_id} temp_existing_concepts
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
        pg_hook.run(observation_number_query)
        logging.info(
            "Successfully added value_as_number for Observation domain concepts"
        )
    except Exception as e:
        logging.error(f"Database error in observation_number_query: {str(e)}")
        raise

    # Add value_as_string to Observation domain concepts with string data types
    observation_string_query = f"""
    -- Update value_as_string_field_id for Observation domain concepts with string data types
    UPDATE temp_existing_concepts_{table_id} temp_existing_concepts
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
        pg_hook.run(observation_string_query)
        logging.info(
            "Successfully added value_as_string for Observation domain concepts"
        )
    except Exception as e:
        logging.error(f"Database error in observation_string_query: {str(e)}")
        raise

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


def find_dest_table_and_person_field_id(**kwargs):
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
    """
    try:
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")
        update_job_status(
            scan_report_id=kwargs.get("dag_run", {}).conf.get("scan_report_id"),
            table_id=table_id,
            stage=JobStageType.GENERATE_RULES,
            status=StageStatusType.IN_PROGRESS,
            details="Finding destination table and field IDs...",
        )
        if not table_id:
            logging.warning(
                "No table_id provided in find_dest_table_and_person_field_id"
            )

        core_query = f"""
        -- Update destination table ID
        UPDATE temp_standard_concepts_{table_id} tsc
        SET dest_table_id = ot.id
        FROM omop.concept std_concept
        LEFT JOIN mapping_omoptable ot ON
            CASE std_concept.domain_id
                WHEN 'Race' THEN 'person'
                WHEN 'Gender' THEN 'person'
                WHEN 'Ethnicity' THEN 'person'
                WHEN 'Observation' THEN 'observation'
                WHEN 'Condition' THEN 'condition_occurrence'
                WHEN 'Device' THEN 'device_exposure'
                WHEN 'Measurement' THEN 'measurement'
                WHEN 'Drug' THEN 'drug_exposure'
                WHEN 'Procedure' THEN 'procedure_occurrence'
                WHEN 'Meas Value' THEN 'measurement'
                WHEN 'Specimen' THEN 'specimen'
                ELSE LOWER(std_concept.domain_id)
            END = ot.table
        WHERE std_concept.concept_id = tsc.standard_concept_id;
        
        -- Update person field ID
        UPDATE temp_standard_concepts_{table_id} tsc
        SET dest_person_field_id = opf.id
        FROM mapping_omopfield opf
        WHERE opf.table_id = tsc.dest_table_id
        AND opf.field = 'person_id';
        """
        try:
            pg_hook.run(core_query)
            logging.info("Successfully added destination table and person field IDs")
        except Exception as e:
            logging.error(
                f"Database error in find_dest_table_and_person_field_id: {str(e)}"
            )
            raise
    except Exception as e:
        logging.error(f"Error in find_dest_table_and_person_field_id: {str(e)}")
        raise


def find_date_fields(**kwargs):
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
    """
    try:
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")
        if not table_id:
            logging.warning("No table_id provided in find_date_fields")

        # Optimized SQL with better structure and reduced redundancy
        dates_query = f"""
        -- Single consolidated update using CASE expressions for better performance
        UPDATE temp_standard_concepts_{table_id} tsc
        SET 
            dest_date_field_id = (
                SELECT mf.id
                FROM mapping_omopfield mf
                JOIN mapping_omoptable mt ON mt.id = mf.table_id
                WHERE mf.table_id = tsc.dest_table_id
                AND (
                    (mt.table = 'person' AND mf.field = 'birth_datetime') OR
                    (mt.table = 'measurement' AND mf.field = 'measurement_datetime') OR
                    (mt.table = 'observation' AND mf.field = 'observation_datetime') OR
                    (mt.table = 'procedure_occurrence' AND mf.field = 'procedure_datetime') OR
                    (mt.table = 'specimen' AND mf.field = 'specimen_datetime')
                )
                LIMIT 1
            ),
            
            dest_start_date_field_id = (
                SELECT mf.id
                FROM mapping_omopfield mf
                JOIN mapping_omoptable mt ON mt.id = mf.table_id
                WHERE mf.table_id = tsc.dest_table_id
                AND (
                    (mt.table = 'condition_occurrence' AND mf.field = 'condition_start_datetime') OR
                    (mt.table = 'drug_exposure' AND mf.field = 'drug_exposure_start_datetime') OR
                    (mt.table = 'device_exposure' AND mf.field = 'device_exposure_start_datetime')
                )
                LIMIT 1
            ),
            
            dest_end_date_field_id = (
                SELECT mf.id
                FROM mapping_omopfield mf
                JOIN mapping_omoptable mt ON mt.id = mf.table_id
                WHERE mf.table_id = tsc.dest_table_id
                AND (
                    (mt.table = 'condition_occurrence' AND mf.field = 'condition_end_datetime') OR
                    (mt.table = 'drug_exposure' AND mf.field = 'drug_exposure_end_datetime') OR
                    (mt.table = 'device_exposure' AND mf.field = 'device_exposure_end_datetime')
                )
                LIMIT 1
            );
        """

        try:
            pg_hook.run(dates_query)
            logging.info(
                "Successfully added date field IDs based on the date field mapper"
            )
        except Exception as e:
            logging.error(f"Database error in find_date_fields: {str(e)}")
            raise
    except Exception as e:
        logging.error(f"Error in find_date_fields: {str(e)}")
        raise


def find_concept_fields(**kwargs):
    """
    Add concept-related field IDs to the temporary concepts table.
    Includes source concept, source value, and destination concept fields.
    Uses domain-specific field patterns with strict table mapping.
    """
    try:
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")

        if not table_id:
            logging.warning("No table_id provided in find_concept_fields")

        # Create a staging table with computed field values
        stage_query = f"""
        -- Create a staging table with the correct field IDs for each record
        CREATE TABLE temp_concept_fields_staging_{table_id} AS
        SELECT 
            tsc.sr_value_id,
            tsc.standard_concept_id,
            c.domain_id,
            -- Use domain-specific source_concept_field_id
            (SELECT mf.id 
            FROM mapping_omopfield mf 
            WHERE mf.table_id = tsc.dest_table_id 
            AND mf.field = LOWER(c.domain_id) || '_source_concept_id'
            LIMIT 1) AS source_concept_field_id,

            -- Use domain-specific source_value_field_id
            (SELECT mf.id 
            FROM mapping_omopfield mf 
            WHERE mf.table_id = tsc.dest_table_id 
            AND mf.field = LOWER(c.domain_id) || '_source_value'
            LIMIT 1) AS source_value_field_id,

            -- Use domain-specific dest_concept_field_id
            (SELECT mf.id 
            FROM mapping_omopfield mf 
            WHERE mf.table_id = tsc.dest_table_id 
            AND mf.field = LOWER(c.domain_id) || '_concept_id'
            LIMIT 1) AS dest_concept_field_id

        FROM temp_standard_concepts_{table_id} tsc
        JOIN omop.concept c ON c.concept_id = tsc.standard_concept_id;
        
        -- Then update the main table from the staging table
        UPDATE temp_standard_concepts_{table_id} tsc
        SET 
            source_concept_field_id = stg.source_concept_field_id,
            source_value_field_id = stg.source_value_field_id,
            dest_concept_field_id = stg.dest_concept_field_id
        FROM temp_concept_fields_staging_{table_id} stg
        WHERE stg.sr_value_id = tsc.sr_value_id
        AND stg.standard_concept_id = tsc.standard_concept_id;
        
        -- Clean up
        DROP TABLE IF EXISTS temp_concept_fields_staging_{table_id};
        """

        try:
            pg_hook.run(stage_query)
            logging.info("Successfully added concept field IDs")
        except Exception as e:
            logging.error(f"Database error in find_concept_fields: {str(e)}")
            raise
    except Exception as e:
        logging.error(f"Error in find_concept_fields: {str(e)}")
        raise


def find_additional_fields(**kwargs):
    """
    Add additional field IDs to the temporary concepts table based on data types.
    Handles measurement domain and observation domain concepts.
    """
    try:
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")
        field_vocab_pairs = process_field_vocab_pairs(
            kwargs.get("dag_run", {}).conf.get("field_vocab_pairs")
        )

        if not field_vocab_pairs:
            logging.error("No field-vocabulary pairs provided")
            raise ValueError("No field-vocabulary pairs provided")

        for pair in field_vocab_pairs:
            field_data_type = pair.get("field_data_type", "").lower()
            numeric_types = ["int", "real", "float", "numeric", "decimal", "double"]
            string_types = ["varchar", "nvarchar", "text", "string", "char"]
            is_string = (
                any(t in field_data_type for t in string_types)
                if field_data_type
                else False
            )
            is_numeric = (
                any(t in field_data_type for t in numeric_types)
                if field_data_type
                else False
            )

            # Always add value_as_number to Measurement domain concepts, but ONLY if they're in the measurement table
            measurement_query = f"""
            -- Update value_as_number_field_id for measurement domain concepts ONLY
            UPDATE temp_standard_concepts_{table_id}
            SET value_as_number_field_id = mf.id
            FROM mapping_omopfield mf, omop.concept c, mapping_omoptable ot
            WHERE 
                c.concept_id = temp_standard_concepts_{table_id}.standard_concept_id AND
                c.domain_id = 'Measurement' AND
                mf.table_id = temp_standard_concepts_{table_id}.dest_table_id AND
                mf.field = 'value_as_number' AND
                ot.id = temp_standard_concepts_{table_id}.dest_table_id AND
                ot.table = 'measurement';
            """

            try:
                pg_hook.run(measurement_query)
                logging.info(
                    "Successfully added value_as_number for Measurement domain concepts"
                )
            except Exception as e:
                logging.error(f"Database error in measurement_query: {str(e)}")
                raise

            # Only add value_as_number to Observation domain concepts with numeric data types
            if is_numeric:
                observation_number_query = f"""
                -- Update value_as_number_field_id for Observation domain concepts with numeric data types
                UPDATE temp_standard_concepts_{table_id}
                SET value_as_number_field_id = mf.id
                FROM mapping_omopfield mf, omop.concept c, mapping_omoptable ot
                WHERE 
                    c.concept_id = temp_standard_concepts_{table_id}.standard_concept_id AND
                    c.domain_id = 'Observation' AND
                    mf.table_id = temp_standard_concepts_{table_id}.dest_table_id AND
                    mf.field = 'value_as_number' AND
                    ot.id = temp_standard_concepts_{table_id}.dest_table_id AND
                    ot.table = 'observation';
                """

                try:
                    pg_hook.run(observation_number_query)
                    logging.info(
                        "Successfully added value_as_number for Observation domain concepts"
                    )
                except Exception as e:
                    logging.error(
                        f"Database error in observation_number_query: {str(e)}"
                    )
                    raise

            # Only add value_as_string to Observation domain concepts with string data types
            if is_string:
                observation_string_query = f"""
                -- Update value_as_string_field_id for Observation domain concepts with string data types
                UPDATE temp_standard_concepts_{table_id}
                SET value_as_string_field_id = mf.id
                FROM mapping_omopfield mf, omop.concept c, mapping_omoptable ot
                WHERE 
                    c.concept_id = temp_standard_concepts_{table_id}.standard_concept_id AND
                    c.domain_id = 'Observation' AND
                    mf.table_id = temp_standard_concepts_{table_id}.dest_table_id AND
                    mf.field = 'value_as_string' AND
                    ot.id = temp_standard_concepts_{table_id}.dest_table_id AND
                    ot.table = 'observation';
                """

                try:
                    pg_hook.run(observation_string_query)
                    logging.info(
                        "Successfully added value_as_string for Observation domain concepts"
                    )
                except Exception as e:
                    logging.error(
                        f"Database error in observation_string_query: {str(e)}"
                    )
                    raise

    except Exception as e:
        logging.error(f"Error in find_additional_fields: {str(e)}")
        raise

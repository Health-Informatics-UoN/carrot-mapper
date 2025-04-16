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

        # Create the temporary table once, outside the loop
        create_table_query = """
        DROP TABLE IF EXISTS temp_standard_concepts;
        CREATE TABLE temp_standard_concepts (
            sr_value_id INTEGER,
            source_concept_id INTEGER,
            standard_concept_id INTEGER
        );
        """
        try:
            pg_hook.run(create_table_query)
            logging.info("Successfully created temp_standard_concepts table")
        except Exception as e:
            logging.error(f"Failed to create temp_standard_concepts table: {str(e)}")
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
            INSERT INTO temp_standard_concepts (sr_value_id, source_concept_id, standard_concept_id)
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


def find_dest_table_and_person_field_id(**kwargs):
    """
    Add destination table IDs and person field IDs to the temporary concepts table.
    """
    try:
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")

        if not table_id:
            logging.warning(
                "No table_id provided in find_dest_table_and_person_field_id"
            )

        core_query = """
        ALTER TABLE temp_standard_concepts 
        ADD COLUMN dest_table_id INTEGER,
        ADD COLUMN dest_person_field_id INTEGER;
        
        -- Update destination table ID
        UPDATE temp_standard_concepts tsc
        SET dest_table_id = ot.id
        FROM omop.concept c2
        LEFT JOIN mapping_omoptable ot ON
            CASE c2.domain_id
                WHEN 'Observation' THEN 'observation'
                WHEN 'Condition' THEN 'condition_occurrence'
                WHEN 'Device' THEN 'device_exposure'
                WHEN 'Measurement' THEN 'measurement'
                WHEN 'Person' THEN 'person'
                WHEN 'Drug' THEN 'drug_exposure'
                WHEN 'Procedure' THEN 'procedure_occurrence'
                WHEN 'Meas Value' THEN 'measurement'
                WHEN 'Specimen' THEN 'specimen'
                ELSE LOWER(c2.domain_id)
            END = ot.table
        WHERE c2.concept_id = tsc.standard_concept_id;
        
        -- Update person field ID
        UPDATE temp_standard_concepts tsc
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
    Uses the predefined mapping between tables and their datetime fields.
    """
    try:
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")
        if not table_id:
            logging.warning("No table_id provided in find_date_fields")

        # Optimized SQL with better structure and reduced redundancy
        dates_query = """
        ALTER TABLE temp_standard_concepts 
        ADD COLUMN dest_date_field_id INTEGER,
        ADD COLUMN dest_start_date_field_id INTEGER,
        ADD COLUMN dest_end_date_field_id INTEGER;

        -- Single consolidated update using CASE expressions for better performance
        UPDATE temp_standard_concepts tsc
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
    """
    try:
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")

        if not table_id:
            logging.warning("No table_id provided in find_concept_fields")

        concept_query = """
        ALTER TABLE temp_standard_concepts 
        ADD COLUMN source_concept_field_id INTEGER,
        ADD COLUMN source_value_field_id INTEGER,
        ADD COLUMN dest_concept_field_id INTEGER;
        
        -- Update source_concept_field_id
        UPDATE temp_standard_concepts tsc
        SET source_concept_field_id = scf.id
        FROM mapping_omopfield scf
        WHERE scf.table_id = tsc.dest_table_id 
        AND scf.field LIKE '%_source_concept_id';

        -- Update source_value_field_id
        UPDATE temp_standard_concepts tsc
        SET source_value_field_id = svf.id
        FROM mapping_omopfield svf
        WHERE svf.table_id = tsc.dest_table_id 
        AND svf.field LIKE '%_source_value';
        
        -- Update dest_concept_field_id
        UPDATE temp_standard_concepts tsc
        SET dest_concept_field_id = dcf.id
        FROM mapping_omopfield dcf
        WHERE dcf.table_id = tsc.dest_table_id 
        AND dcf.field LIKE '%_concept_id'
        AND dcf.field NOT LIKE '%_source_concept_id';
        """
        try:
            pg_hook.run(concept_query)
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
        table_id, field_vocab_pairs = extract_params(**kwargs)

        if not field_vocab_pairs:
            logging.error("No field-vocabulary pairs provided")
            raise ValueError("No field-vocabulary pairs provided")

        for pair in field_vocab_pairs:
            field_data_type = pair.get("field_data_type", "").lower()
            numeric_types = ["int", "real", "float"]
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

            value_as_number_query = f"""
            ALTER TABLE temp_standard_concepts 
            ADD COLUMN IF NOT EXISTS value_as_number_field_id INTEGER,
            ADD COLUMN IF NOT EXISTS value_as_string_field_id INTEGER,
            ADD COLUMN IF NOT EXISTS value_as_concept_field_id INTEGER;

            -- Update value_as_number_field_id for measurement domain concepts
            WITH measurement_concepts AS (
                SELECT tsc.sr_value_id, tsc.standard_concept_id, tsc.dest_table_id
                FROM temp_standard_concepts tsc
                JOIN omop.concept c ON c.concept_id = tsc.standard_concept_id
                WHERE c.domain_id = 'Measurement'
            )
            UPDATE temp_standard_concepts tsc
            SET value_as_number_field_id = mf.id
            FROM measurement_concepts mc
            JOIN mapping_omopfield mf ON mf.table_id = mc.dest_table_id AND mf.field = 'value_as_number'
            WHERE tsc.sr_value_id = mc.sr_value_id;

            -- Update value_as_number_field_id for Meas Value domain concepts
            WITH meas_value_concepts AS (
                SELECT tsc.sr_value_id, tsc.standard_concept_id, tsc.dest_table_id
                FROM temp_standard_concepts tsc
                JOIN omop.concept c ON c.concept_id = tsc.standard_concept_id
                WHERE c.domain_id = 'Meas Value'
            )
            UPDATE temp_standard_concepts tsc
            SET value_as_concept_field_id = mf.id
            FROM meas_value_concepts mvc
            JOIN mapping_omopfield mf ON mf.table_id = mvc.dest_table_id AND mf.field = 'value_as_concept_id'
            WHERE tsc.sr_value_id = mvc.sr_value_id;
            """

            # Only add the observation domain logic if the field data type is numeric
            if is_numeric:
                value_as_number_query += """
            -- Update value_as_number_field_id for observation domain concepts with numeric data types
            WITH observation_concepts AS (
                SELECT tsc.sr_value_id, tsc.standard_concept_id, tsc.dest_table_id
                FROM temp_standard_concepts tsc
                JOIN omop.concept c ON c.concept_id = tsc.standard_concept_id
                WHERE c.domain_id = 'Observation'
            )
            UPDATE temp_standard_concepts tsc
            SET value_as_number_field_id = of.id
            FROM observation_concepts oc
            JOIN mapping_omopfield of ON of.table_id = oc.dest_table_id AND of.field = 'value_as_number'
            WHERE tsc.sr_value_id = oc.sr_value_id;
            """

            if is_string:
                value_as_number_query += """
            -- Update value_as_string_field_id for observation domain concepts with string data types
            WITH observation_concepts AS (
                SELECT tsc.sr_value_id, tsc.standard_concept_id, tsc.dest_table_id
                FROM temp_standard_concepts tsc
                JOIN omop.concept c ON c.concept_id = tsc.standard_concept_id
                WHERE c.domain_id = 'Observation'
            )
            UPDATE temp_standard_concepts tsc
            SET value_as_string_field_id = of.id
            FROM observation_concepts oc
            JOIN mapping_omopfield of ON of.table_id = oc.dest_table_id AND of.field = 'value_as_string'
            WHERE tsc.sr_value_id = oc.sr_value_id;
            """

            try:
                pg_hook.run(value_as_number_query)
                logging.info(
                    f"Successfully added additional fields for data type {field_data_type}"
                )
            except Exception as e:
                logging.error(
                    f"Database error in find_additional_fields for data type {field_data_type}: {str(e)}"
                )
                raise
    except Exception as e:
        logging.error(f"Error in find_additional_fields: {str(e)}")
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

        create_concept_query = """
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
            FROM temp_standard_concepts tsc
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

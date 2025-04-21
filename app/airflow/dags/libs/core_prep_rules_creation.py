from libs.utils import extract_params
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


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

        core_query = f"""
        ALTER TABLE temp_standard_concepts_{table_id} 
        ADD COLUMN dest_table_id INTEGER,
        ADD COLUMN dest_person_field_id INTEGER;
        
        -- Update destination table ID
        UPDATE temp_standard_concepts_{table_id} tsc
        SET dest_table_id = ot.id
        FROM omop.concept c2
        LEFT JOIN mapping_omoptable ot ON
            CASE c2.domain_id
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
                ELSE LOWER(c2.domain_id)
            END = ot.table
        WHERE c2.concept_id = tsc.standard_concept_id;
        
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
    Uses the predefined mapping between tables and their datetime fields.
    """
    try:
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")
        if not table_id:
            logging.warning("No table_id provided in find_date_fields")

        # Optimized SQL with better structure and reduced redundancy
        dates_query = f"""
        ALTER TABLE temp_standard_concepts_{table_id} 
        ADD COLUMN dest_date_field_id INTEGER,
        ADD COLUMN dest_start_date_field_id INTEGER,
        ADD COLUMN dest_end_date_field_id INTEGER;

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
    For person table, handles gender, race, and ethnicity domains separately.
    """
    try:
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")

        if not table_id:
            logging.warning("No table_id provided in find_concept_fields")

        # First, add the standard columns
        base_query = f"""
        ALTER TABLE temp_standard_concepts_{table_id} 
        ADD COLUMN source_concept_field_id INTEGER,
        ADD COLUMN source_value_field_id INTEGER,
        ADD COLUMN dest_concept_field_id INTEGER;
        """

        # Person table specific handling based on domain
        person_specific_query = f"""
        -- For person table, update based on domain_id
        WITH domain_field_map AS (
            SELECT 
                tsc.sr_value_id,
                c.domain_id,
                LOWER(c.domain_id) AS field_prefix,
                MAX(CASE WHEN mf.field = LOWER(c.domain_id) || '_source_concept_id' THEN mf.id END) AS source_concept_field_id,
                MAX(CASE WHEN mf.field = LOWER(c.domain_id) || '_source_value' THEN mf.id END) AS source_value_field_id,
                MAX(CASE WHEN mf.field = LOWER(c.domain_id) || '_concept_id' THEN mf.id END) AS dest_concept_field_id
            FROM temp_standard_concepts_{table_id} tsc
            JOIN omop.concept c ON c.concept_id = tsc.standard_concept_id
            JOIN mapping_omoptable ot ON ot.table = 'person' AND tsc.dest_table_id = ot.id
            JOIN mapping_omopfield mf ON mf.table_id = ot.id
            WHERE c.domain_id IN ('Gender', 'Race', 'Ethnicity')
            GROUP BY tsc.sr_value_id, c.domain_id
        )
        UPDATE temp_standard_concepts_{table_id} tsc
        SET 
            source_concept_field_id = dfm.source_concept_field_id,
            source_value_field_id = dfm.source_value_field_id,
            dest_concept_field_id = dfm.dest_concept_field_id
        FROM domain_field_map dfm
        WHERE dfm.sr_value_id = tsc.sr_value_id;
        """

        # For non-person tables or unmatched domains, use generic pattern matching in a single update
        non_person_query = f"""
        WITH field_mappings AS (
            SELECT 
                tsc.sr_value_id,
                MAX(CASE WHEN mf.field LIKE '%_source_concept_id' THEN mf.id END) AS source_concept_field_id,
                MAX(CASE WHEN mf.field LIKE '%_source_value' THEN mf.id END) AS source_value_field_id,
                MAX(CASE WHEN mf.field LIKE '%_concept_id' AND mf.field NOT LIKE '%_source_concept_id' THEN mf.id END) AS dest_concept_field_id
            FROM temp_standard_concepts_{table_id} tsc
            JOIN mapping_omopfield mf ON mf.table_id = tsc.dest_table_id
            WHERE tsc.source_concept_field_id IS NULL 
               OR tsc.source_value_field_id IS NULL 
               OR tsc.dest_concept_field_id IS NULL
            GROUP BY tsc.sr_value_id
        )
        UPDATE temp_standard_concepts_{table_id} tsc
        SET 
            source_concept_field_id = COALESCE(tsc.source_concept_field_id, fm.source_concept_field_id),
            source_value_field_id = COALESCE(tsc.source_value_field_id, fm.source_value_field_id),
            dest_concept_field_id = COALESCE(tsc.dest_concept_field_id, fm.dest_concept_field_id)
        FROM field_mappings fm
        WHERE fm.sr_value_id = tsc.sr_value_id;
        """

        # Combine queries
        concept_query = base_query + person_specific_query

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
            ALTER TABLE temp_standard_concepts_{table_id} 
            ADD COLUMN IF NOT EXISTS value_as_number_field_id INTEGER,
            ADD COLUMN IF NOT EXISTS value_as_string_field_id INTEGER;

            -- Update value_as_number_field_id for measurement domain concepts
            WITH measurement_concepts AS (
                SELECT tsc.sr_value_id, tsc.standard_concept_id, tsc.dest_table_id
                FROM temp_standard_concepts_{table_id} tsc
                JOIN omop.concept c ON c.concept_id = tsc.standard_concept_id
                WHERE c.domain_id = 'Measurement'
            )
            UPDATE temp_standard_concepts_{table_id} tsc
            SET value_as_number_field_id = mf.id
            FROM measurement_concepts mc
            JOIN mapping_omopfield mf ON mf.table_id = mc.dest_table_id AND mf.field = 'value_as_number'
            WHERE tsc.sr_value_id = mc.sr_value_id;
            """

            # TODO: refine and find solution for value_as_concept_field_id
            # ADD COLUMN IF NOT EXISTS value_as_concept_field_id INTEGER;
            # -- Update value_as_concept_field_id for concepts
            # WITH meas_value_concepts AS (
            #     SELECT tsc.sr_value_id, tsc.standard_concept_id, tsc.dest_table_id
            #     FROM temp_standard_concepts tsc
            #     JOIN omop.concept c ON c.concept_id = tsc.standard_concept_id
            #     WHERE c.domain_id = 'Meas Value' -- TODO: do this for domains Observation and Measurement
            # )
            # UPDATE temp_standard_concepts tsc
            # SET value_as_concept_field_id = mf.id
            # FROM meas_value_concepts mvc
            # JOIN mapping_omopfield mf ON mf.table_id = mvc.dest_table_id AND mf.field = 'value_as_concept_id'
            # WHERE tsc.sr_value_id = mvc.sr_value_id;

            # Only add the observation domain logic if the field data type is numeric
            if is_numeric:
                value_as_number_query += f"""
            -- Update value_as_number_field_id for observation domain concepts with numeric data types
            WITH observation_concepts AS (
                SELECT tsc.sr_value_id, tsc.standard_concept_id, tsc.dest_table_id
                FROM temp_standard_concepts_{table_id} tsc
                JOIN omop.concept c ON c.concept_id = tsc.standard_concept_id
                WHERE c.domain_id = 'Observation'
            )
            UPDATE temp_standard_concepts_{table_id} tsc
            SET value_as_number_field_id = of.id
            FROM observation_concepts oc
            JOIN mapping_omopfield of ON of.table_id = oc.dest_table_id AND of.field = 'value_as_number'
            WHERE tsc.sr_value_id = oc.sr_value_id;
            """

            if is_string:
                value_as_number_query += f"""
            -- Update value_as_string_field_id for observation domain concepts with string data types
            WITH observation_concepts AS (
                SELECT tsc.sr_value_id, tsc.standard_concept_id, tsc.dest_table_id
                FROM temp_standard_concepts_{table_id} tsc
                JOIN omop.concept c ON c.concept_id = tsc.standard_concept_id
                WHERE c.domain_id = 'Observation'
            )
            UPDATE temp_standard_concepts_{table_id} tsc
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

from libs.utils import extract_params
from airflow.providers.postgres.hooks.postgres import PostgresHook

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


# TODO: more error handling and docstring
def find_standard_concepts(**kwargs):

    table_id, field_vocab_pairs = extract_params(**kwargs)

    for pair in field_vocab_pairs:

        sr_field_id = pair.get("sr_field_id")
        vocabulary_id = pair.get("vocabulary_id") 

        if not sr_field_id or not vocabulary_id:
            raise ValueError(
                "Invalid field_vocab_pair: requires sr_field_id and vocabulary_id"
            )

        # Step 1: Form base table (sr_value_id, source_concept_id, standard_concept_id)
        standard_concepts_query = f"""
        DROP TABLE IF EXISTS temp_standard_concepts;
        CREATE TABLE temp_standard_concepts AS
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
        pg_hook.run(standard_concepts_query)


def find_dest_table_and_person_field_id(**kwargs):
    
    # TODO: add docstring
    # Step 2: Add columns dest_table_id and dest_person_field_id

    table_id = kwargs["dag_run"].conf.get("table_id")

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
            -- TODO: having tests for the case when the domain is Specimen
            WHEN 'Specimen' THEN 'specimen'
            -- TODO: plan for other domains: Death, Specimen, etc. and for the case when the domain is not supported
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
    pg_hook.run(core_query)


def find_date_fields(**kwargs):
    
    # TODO: add docstring
    # Step 3: Add columns about dates: dest_date_field_id, dest_start_date_field_id, dest_end_date_field_id
    # TODO: generate for both date and datetime fields in OMOP tables
    table_id = kwargs["dag_run"].conf.get("table_id")
    
    dates_query = """
    ALTER TABLE temp_standard_concepts 
    ADD COLUMN dest_date_field_id INTEGER,
    ADD COLUMN dest_start_date_field_id INTEGER,
    ADD COLUMN dest_end_date_field_id INTEGER;

    -- Add all date fields in one go
    WITH date_field_analysis AS (
        SELECT 
            tsc.sr_value_id,
            MIN(df.id) AS min_id,
            MAX(df.id) AS max_id,
            COUNT(*) AS count
        FROM temp_standard_concepts tsc
        JOIN mapping_omopfield df ON
            df.table_id = tsc.dest_table_id AND
            df.field LIKE '%datetime'
        GROUP BY tsc.sr_value_id
    )
    UPDATE temp_standard_concepts tsc
    SET 
        dest_date_field_id = CASE WHEN dfa.count = 1 THEN dfa.min_id ELSE NULL END,
        dest_start_date_field_id = CASE WHEN dfa.count > 1 THEN dfa.min_id ELSE NULL END,
        dest_end_date_field_id = CASE WHEN dfa.count > 1 THEN dfa.max_id ELSE NULL END
    FROM date_field_analysis dfa
    WHERE dfa.sr_value_id = tsc.sr_value_id;
    """
    pg_hook.run(dates_query)


def find_concept_fields(**kwargs):
    # TODO: add docstring
    # Step 4: Add columns for source concept, source value, and destination concept fields
    table_id = kwargs["dag_run"].conf.get("table_id")


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
    pg_hook.run(concept_query)


def find_additional_fields(**kwargs):
    # TODO: add docstring
    # Step 5: Add value_as_number column for measurement domain concepts
    # TODO: find the way to simplify this logic
    table_id, field_vocab_pairs = extract_params(**kwargs)

    for pair in field_vocab_pairs:

        field_data_type = pair.get("field_data_type", "").lower()  # Extract field_data_type from the pair
        numeric_types = ["int", "real", "float"]
        string_types = ["varchar", "nvarchar", "text", "string", "char"]
        is_string = any(t in field_data_type for t in string_types) if field_data_type else False
        is_numeric = any(t in field_data_type for t in numeric_types) if field_data_type else False

        value_as_number_query = f"""
        ALTER TABLE temp_standard_concepts 
        ADD COLUMN value_as_number_field_id INTEGER,
        ADD COLUMN value_as_string_field_id INTEGER,
        ADD COLUMN value_as_concept_field_id INTEGER;

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
        -- TODO: MEAS VALUE:This domain can barely be used in auto-mapping needs discussion with the team
        -- TODO: need reviewing and testing
        -- TODO: in the SR when the data type is varchar, Carrot will irgnore the numberic value???
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

        pg_hook.run(value_as_number_query)

def create_standard_concepts(**kwargs):
    # TODO: add docstring
    # Step 6: Create standard concepts for field values
    table_id = kwargs["dag_run"].conf.get("table_id")
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

    pg_hook.run(create_concept_query)

from libs.utils import extract_params
from airflow.providers.postgres.hooks.postgres import PostgresHook

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


# TODO: more error handling and docstring
def find_and_create_standard_concepts(**kwargs):

    table_id, field_vocab_pairs = extract_params(**kwargs)

    for pair in field_vocab_pairs:

        sr_field_id = pair.get("sr_field_id")
        vocabulary_id = pair.get("vocabulary_id")

        if not sr_field_id or not vocabulary_id:
            raise ValueError(
                "Invalid field_vocab_pair: requires sr_field_id and vocabulary_id"
            )

        # Step 1: Form base table with columns 1 & 2 (sr_value_id and standard_concept_id)
        step1_query = f"""
        DROP TABLE IF EXISTS temp_standard_concepts;
        CREATE TABLE temp_standard_concepts AS
        SELECT
            srv.id AS sr_value_id,
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
        pg_hook.run(step1_query)
        
        # Step 2: Add columns 3 & 4 (dest_table_id and dest_person_field_id)
        step2_query = """
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
        pg_hook.run(step2_query)
        
        # Step 3: Add columns 5, 6, 7 (date fields) with simpler implementation
        step3_query = """
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
        pg_hook.run(step3_query)

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

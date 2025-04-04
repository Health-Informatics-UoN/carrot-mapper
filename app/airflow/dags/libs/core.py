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

        find_std_concept_query = f"""
        DROP TABLE IF EXISTS temp_standard_concepts;
        CREATE TABLE temp_standard_concepts AS
        SELECT
            srv.id AS sr_value_id,
            c2.concept_id AS standard_concept_id,
            ot.id AS dest_table_id,
            opf.id AS dest_person_field_id
        -- Column 1: sr_value_id from scanreportvalue table
        FROM mapping_scanreportvalue srv
        -- Column 2: concept_id from vocabulary table which fullfiled conditions
        JOIN omop.concept c1 ON
            c1.concept_code = srv.value AND
            c1.vocabulary_id = '{vocabulary_id}'
        JOIN omop.concept_relationship cr ON
            cr.concept_id_1 = c1.concept_id AND
            cr.relationship_id = 'Maps to'
        JOIN omop.concept c2 ON
            c2.concept_id = cr.concept_id_2 AND
            c2.standard_concept = 'S'
        -- Column 3: destination_table_id from omoptable table
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
        -- Column 4: Dest. OMOP field for Person ID
        LEFT JOIN mapping_omopfield opf ON
            opf.table_id = ot.id AND
            opf.field = 'person_id'
        -- Supporting the first column
        WHERE srv.scan_report_field_id = {sr_field_id};
        """

        pg_hook.run(find_std_concept_query)

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

create_existing_concepts_table_query = """
    DROP TABLE IF EXISTS temp_existing_concepts_%(table_id)s;
    CREATE TABLE temp_existing_concepts_%(table_id)s (
        object_id INTEGER,
        sr_concept_id INTEGER,
        content_type_id INTEGER,
        source_concept_id INTEGER,
        -- TODO: when we can distinguish between source and standard concepts, we can add value to this column
        standard_concept_id INTEGER,
        source_field_id INTEGER,
        source_field_data_type TEXT,
        dest_table_id INTEGER,
        dest_person_field_id INTEGER,
        dest_date_field_id INTEGER,
        dest_start_date_field_id INTEGER,
        dest_end_date_field_id INTEGER,
        dest_concept_field_id INTEGER,
        omop_source_concept_field_id INTEGER,
        omop_source_value_field_id INTEGER,
        value_as_number_field_id INTEGER,
        value_as_string_field_id INTEGER
    );
    """


find_existing_concepts_query = """
    INSERT INTO temp_existing_concepts_%(table_id)s (
        object_id, sr_concept_id, source_concept_id, content_type_id
    )
    SELECT 
        sr_concept.object_id,
        sr_concept.id AS sr_concept_id,
        sr_concept.concept_id AS source_concept_id,
        -- TODO: when we can distinguish between source and standard concepts, we can add value to this column
        -- sr_concept.standard_concept_id AS standard_concept_id
        sr_concept.content_type_id
    FROM mapping_scanreportconcept AS sr_concept
    WHERE 
        (
            -- For ScanReportField
            sr_concept.content_type_id = (
                SELECT id FROM django_content_type 
                WHERE app_label = 'mapping' AND model = 'scanreportfield'
            )
            AND sr_concept.object_id IN (
                SELECT sr_field.id 
                FROM mapping_scanreportfield AS sr_field 
                JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
                WHERE sr_table.scan_report_id = %(scan_report_id)s AND sr_table.id = %(table_id)s
            )
        )
        OR
        (
            -- For ScanReportValue
            sr_concept.content_type_id = (
                SELECT id FROM django_content_type 
                WHERE app_label = 'mapping' AND model = 'scanreportvalue'
            )
            AND sr_concept.object_id IN (
                SELECT sr_value.id 
                FROM mapping_scanreportvalue AS sr_value
                JOIN mapping_scanreportfield AS sr_field ON sr_value.scan_report_field_id = sr_field.id
                JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
                WHERE sr_table.scan_report_id = %(scan_report_id)s AND sr_table.id = %(table_id)s
            )
        );
        """

# This is the source field for concepts-related mapping rules created in the next step
find_source_field_id_query = """
    -- First set the source_field_id
    UPDATE temp_existing_concepts_%(table_id)s AS temp_table
    SET source_field_id =
        CASE
            WHEN temp_table.content_type_id = (
                SELECT id FROM django_content_type 
                WHERE app_label = 'mapping' AND model = 'scanreportfield'
            ) THEN temp_table.object_id
            WHEN temp_table.content_type_id = (
                SELECT id FROM django_content_type 
                WHERE app_label = 'mapping' AND model = 'scanreportvalue'
            ) THEN (
                SELECT sr_value.scan_report_field_id
                FROM mapping_scanreportvalue AS sr_value
                WHERE sr_value.id = temp_table.object_id
            )
            ELSE NULL
        END;

    -- Then use the now-set source_field_id to set data type
    UPDATE temp_existing_concepts_%(table_id)s AS temp_table
    SET source_field_data_type = 
        CASE
            WHEN UPPER(sr_field.type_column) = 'INT' OR
                UPPER(sr_field.type_column) = 'TINYINT' OR
                UPPER(sr_field.type_column) = 'SMALLINT' OR
                UPPER(sr_field.type_column) = 'BIGINT' OR
                UPPER(sr_field.type_column) = 'REAL' OR
                UPPER(sr_field.type_column) = 'FLOAT' OR
                UPPER(sr_field.type_column) = 'NUMERIC' OR
                UPPER(sr_field.type_column) = 'DECIMAL' OR
                UPPER(sr_field.type_column) = 'DOUBLE'
            THEN 'numeric'
            WHEN UPPER(sr_field.type_column) = 'VARCHAR' OR
                UPPER(sr_field.type_column) = 'NVARCHAR' OR
                UPPER(sr_field.type_column) = 'TEXT' OR
                UPPER(sr_field.type_column) = 'STRING' OR
                UPPER(sr_field.type_column) = 'CHAR'
            THEN 'string'
            ELSE sr_field.type_column
        END
    FROM mapping_scanreportfield AS sr_field
    WHERE sr_field.id = temp_table.source_field_id
    AND temp_table.source_field_id IS NOT NULL;
    """


find_dest_table_and_person_field_id_query = """
-- Update destination table ID
UPDATE temp_existing_concepts_%(table_id)s temp_existing_concepts
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
        WHEN 'Spec Anatomic Site' THEN 'specimen'
        ELSE LOWER(target_concept.domain_id)
    END = omop_table.table
-- Because concepts may or may not have the standard_concept_id, in general. And we prefer to use the standard_concept_id, if it exists.
WHERE target_concept.concept_id = COALESCE(temp_existing_concepts.standard_concept_id, temp_existing_concepts.source_concept_id);

-- Update person field ID
UPDATE temp_existing_concepts_%(table_id)s temp_existing_concepts
SET dest_person_field_id = omop_field.id
FROM mapping_omopfield omop_field
WHERE omop_field.table_id = temp_existing_concepts.dest_table_id
AND omop_field.field = 'person_id';
"""

find_dates_fields_query = """
-- Single consolidated update using CASE expressions for better performance
UPDATE temp_existing_concepts_%(table_id)s temp_existing_concepts
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

# Create a staging table with computed field values
find_concept_fields_query = """
-- Prevent duplicate creation of the staging table, in case of re-running the DAG after a bug fix
DROP TABLE IF EXISTS temp_concept_fields_staging_%(table_id)s;
-- Create a staging table with the correct field IDs for each record
CREATE TABLE temp_concept_fields_staging_%(table_id)s AS
SELECT 
    temp_existing_concepts.object_id,
    target_concept.domain_id,
    target_concept.concept_id AS concept_id,
    -- Use domain-specific source_concept_field_id
    (SELECT omop_field.id 
    FROM mapping_omopfield AS omop_field 
    WHERE omop_field.table_id = temp_existing_concepts.dest_table_id 
    AND omop_field.field = 
        CASE 
            WHEN target_concept.domain_id = 'Spec Anatomic Site' THEN 'anatomic_site_source_concept_id'  -- Not applicable for Specimen table
            ELSE LOWER(target_concept.domain_id) || '_source_concept_id'
        END
    LIMIT 1) AS source_concept_field_id,

    -- Use domain-specific source_value_field_id
    (SELECT omop_field.id 
    FROM mapping_omopfield AS omop_field 
    WHERE omop_field.table_id = temp_existing_concepts.dest_table_id 
    AND omop_field.field = 
        CASE 
            WHEN target_concept.domain_id = 'Spec Anatomic Site' THEN 'anatomic_site_source_value'
            ELSE LOWER(target_concept.domain_id) || '_source_value'
        END
    LIMIT 1) AS source_value_field_id,

    -- Use domain-specific dest_concept_field_id
    (SELECT omop_field.id 
    FROM mapping_omopfield AS omop_field 
    WHERE omop_field.table_id = temp_existing_concepts.dest_table_id 
    AND omop_field.field = 
        CASE 
            WHEN target_concept.domain_id = 'Spec Anatomic Site' THEN 'anatomic_site_concept_id'
            ELSE LOWER(target_concept.domain_id) || '_concept_id'
        END
    LIMIT 1) AS dest_concept_field_id

FROM temp_existing_concepts_%(table_id)s temp_existing_concepts
JOIN omop.concept AS target_concept ON target_concept.concept_id = COALESCE(temp_existing_concepts.standard_concept_id, temp_existing_concepts.source_concept_id);

-- Then update the main table from the staging table
UPDATE temp_existing_concepts_%(table_id)s temp_existing_concepts
SET 
    omop_source_concept_field_id = temp_staging_table.source_concept_field_id,
    omop_source_value_field_id = temp_staging_table.source_value_field_id,
    dest_concept_field_id = temp_staging_table.dest_concept_field_id
FROM temp_concept_fields_staging_%(table_id)s temp_staging_table
WHERE temp_staging_table.object_id = temp_existing_concepts.object_id
AND temp_staging_table.concept_id = COALESCE(temp_existing_concepts.standard_concept_id, temp_existing_concepts.source_concept_id);

-- Clean up
DROP TABLE IF EXISTS temp_concept_fields_staging_%(table_id)s;
"""

# Create a temp table for reuse concepts
create_temp_reuse_table_query = """
-- Prevent duplicate creation of the temp reuse concepts table, in case of re-running the DAG after a bug fix
DROP TABLE IF EXISTS temp_reuse_concepts_%(table_id)s;
CREATE TABLE temp_reuse_concepts_%(table_id)s (
    object_id INTEGER,
    matching_value_name TEXT,
    matching_value_description TEXT,
    matching_field_name TEXT,
    matching_table_name TEXT,
    -- TODO: when we can distinguish the source concept id/ concept_id for the model SCANREPORTCONCEPT/ M concepts, we need to work more here
    source_scanreport_id INTEGER,
    content_type_id INTEGER,
    concept_id INTEGER
);
"""


# Find values with M-type concepts in eligible scan reports
find_m_concepts_query = """
WITH
    -- Get the content type id for scanreportvalue
    value_content_type AS (
        SELECT id FROM django_content_type
        WHERE app_label = 'mapping' AND model = 'scanreportvalue'
        LIMIT 1
    ),
    -- Get all eligible scan reports in the same dataset, completed, not hidden, not the current one
    eligible_reports AS (
        SELECT scan_report.id
        FROM mapping_scanreport scan_report
        JOIN mapping_dataset dataset ON scan_report.parent_dataset_id = dataset.id
        JOIN mapping_mappingstatus map_status ON scan_report.mapping_status_id = map_status.id
        WHERE dataset.id = %(parent_dataset_id)s
            AND dataset.hidden = FALSE
            AND scan_report.hidden = FALSE
            AND map_status.value = 'COMPLETE'
            AND scan_report.id != %(scan_report_id)s
    ),
    -- Find values in eligible scan reports that have M-type concepts tied
    values_with_m_concepts AS (
        SELECT
            sr_value.value AS matching_value_name,
            sr_value.value_description AS matching_value_description,
            sr_field.name AS matching_field_name,
            sr_table.name AS matching_table_name,
            value_content_type.id AS content_type_id,
            sr_concept.concept_id AS concept_id,
            eligible_report.id AS source_scanreport_id
        FROM eligible_reports AS eligible_report
        JOIN mapping_scanreporttable AS sr_table ON sr_table.scan_report_id = eligible_report.id
            AND sr_table.name = %(current_table_name)s
        JOIN mapping_scanreportfield AS sr_field ON sr_field.scan_report_table_id = sr_table.id
        JOIN mapping_scanreportvalue AS sr_value ON sr_value.scan_report_field_id = sr_field.id
        JOIN mapping_scanreportconcept AS sr_concept ON sr_concept.object_id = sr_value.id
            AND sr_concept.content_type_id = (SELECT id FROM value_content_type)
            AND (sr_concept.creation_type = 'M' OR sr_concept.creation_type = 'R')
        CROSS JOIN value_content_type
    )
INSERT INTO temp_reuse_concepts_%(table_id)s (
    matching_value_name, matching_value_description, matching_field_name, matching_table_name, 
    content_type_id, concept_id, source_scanreport_id
)
SELECT 
    matching_value_name, matching_value_description, matching_field_name, matching_table_name, 
    content_type_id, concept_id, source_scanreport_id
FROM values_with_m_concepts;
"""


# Find fields with M-type concepts in eligible scan reports
find_m_concepts_query_field_level = """
WITH
    -- Get the content type id for scanreportfield
    field_content_type AS (
        SELECT id FROM django_content_type
        WHERE app_label = 'mapping' AND model = 'scanreportfield'
        LIMIT 1
    ),
    -- Get all eligible scan reports in the same dataset, completed, not hidden, not the current one
    eligible_reports AS (
        SELECT scan_report.id
        FROM mapping_scanreport scan_report
        JOIN mapping_dataset dataset ON scan_report.parent_dataset_id = dataset.id
        JOIN mapping_mappingstatus map_status ON scan_report.mapping_status_id = map_status.id
        WHERE dataset.id = %(parent_dataset_id)s
            AND dataset.hidden = FALSE
            AND scan_report.hidden = FALSE
            AND map_status.value = 'COMPLETE'
            AND scan_report.id != %(scan_report_id)s
    ),
    -- Find fields in eligible scan reports that have M-type concepts tied
    fields_with_m_concepts AS (
        SELECT
            sr_field.name AS matching_field_name,
            sr_table.name AS matching_table_name,
            field_content_type.id AS content_type_id,
            sr_concept.concept_id AS concept_id,
            eligible_report.id AS source_scanreport_id
        FROM eligible_reports AS eligible_report
        JOIN mapping_scanreporttable AS sr_table ON sr_table.scan_report_id = eligible_report.id
            AND sr_table.name = %(current_table_name)s
        JOIN mapping_scanreportfield AS sr_field ON sr_field.scan_report_table_id = sr_table.id
        JOIN mapping_scanreportconcept AS sr_concept ON sr_concept.object_id = sr_field.id
            AND sr_concept.content_type_id = (SELECT id FROM field_content_type)
            AND (sr_concept.creation_type = 'M' OR sr_concept.creation_type = 'R')
        CROSS JOIN field_content_type
    )
INSERT INTO temp_reuse_concepts_%(table_id)s (
    matching_field_name, matching_table_name, 
    content_type_id, concept_id, source_scanreport_id
)
SELECT 
    matching_field_name, matching_table_name, 
    content_type_id, concept_id, source_scanreport_id
FROM fields_with_m_concepts;
"""

find_object_id_query = """
    UPDATE temp_reuse_concepts_%(table_id)s AS temp_table
        SET object_id = 
            CASE 
                WHEN temp_table.content_type_id = (
                    SELECT id FROM django_content_type 
                    WHERE app_label = 'mapping' AND model = 'scanreportfield'
                ) THEN  -- For ScanReportField
                    (SELECT sr_field.id 
                    FROM mapping_scanreportfield AS sr_field 
                    JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
                    WHERE sr_table.id = %(table_id)s
                    AND sr_field.name = temp_table.matching_field_name
                    AND sr_table.name = temp_table.matching_table_name
                    LIMIT 1)
                WHEN temp_table.content_type_id = (
                    SELECT id FROM django_content_type 
                    WHERE app_label = 'mapping' AND model = 'scanreportvalue'
                ) THEN  -- For ScanReportValue
                    (SELECT sr_value.id 
                    FROM mapping_scanreportvalue AS sr_value
                    JOIN mapping_scanreportfield AS sr_field ON sr_value.scan_report_field_id = sr_field.id
                    JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
                    WHERE sr_table.id = %(table_id)s
                    AND sr_value.value = temp_table.matching_value_name
                    AND sr_field.name = temp_table.matching_field_name
                    AND sr_table.name = temp_table.matching_table_name
                    AND (
                            (sr_value.value_description = temp_table.matching_value_description)
                            OR (sr_value.value_description IS NULL AND temp_table.matching_value_description IS NULL)
                        )
                    LIMIT 1)
                ELSE NULL
            END;
"""


validate_reused_concepts_query = """
-- Remove duplicates first (without joining omop.concept)
DELETE FROM temp_reuse_concepts_%(table_id)s AS temp_table
USING temp_reuse_concepts_%(table_id)s AS temp_table_duplicate
WHERE (
    -- Remove duplicates at the value level, keeping the one with the lowest source_scanreport_id
    (
        temp_table.object_id = temp_table_duplicate.object_id
        AND temp_table.concept_id = temp_table_duplicate.concept_id
        -- TODO: add standard_concept_id matching check (future) here
        AND temp_table.content_type_id = (SELECT id FROM django_content_type WHERE app_label = 'mapping' AND model = 'scanreportvalue')
        AND temp_table.source_scanreport_id > temp_table_duplicate.source_scanreport_id
    )
    OR
    -- Remove duplicates at the field level, keeping the one with the lowest source_scanreport_id
    (    
        temp_table.object_id = temp_table_duplicate.object_id
        AND temp_table.concept_id = temp_table_duplicate.concept_id
        -- TODO: add standard_concept_id matching check (future) here
        AND temp_table.content_type_id = (
            SELECT id FROM django_content_type 
            WHERE app_label = 'mapping' AND model = 'scanreportfield'
        )
        AND temp_table.source_scanreport_id > temp_table_duplicate.source_scanreport_id
    )
);

-- Remove concepts whose domain is not in the allowed domains
DELETE FROM temp_reuse_concepts_%(table_id)s AS temp_table
USING omop.concept AS omop_concept
WHERE temp_table.concept_id = omop_concept.concept_id
AND omop_concept.domain_id NOT IN (
    'Condition', 'Drug', 'Procedure', 'Specimen', 'Device',
    'Measurement', 'Observation', 'Gender', 'Race', 'Ethnicity', 'Spec Anatomic Site'
);

-- Delete concepts that have no object_id
DELETE FROM temp_reuse_concepts_%(table_id)s
WHERE object_id IS NULL;
"""


# TODO: when source_concept_id is added to the model SCANREPORTCONCEPT, we need to update the query belowto solve the issue #1006
create_reuse_concept_query = """
    -- Insert standard concepts for field values (only if they don't already exist)
    INSERT INTO mapping_scanreportconcept (
        created_at,
        updated_at,
        object_id,
        creation_type,
        -- TODO: Will have the standard_concept_id (nullable) here
        concept_id,
        content_type_id
    )
    SELECT
        NOW(),
        NOW(),
        temp_reuse_concepts.object_id,
        'R',       -- Creation type: Reused
        -- TODO: if standard_concept_id is null then we need to use the source_concept_id
        -- TODO: add standard_concept_id here for the newly creted SR concepts
        temp_reuse_concepts.concept_id,
        temp_reuse_concepts.content_type_id -- content_type_id for scanreportvalue/scanreportfield
    FROM temp_reuse_concepts_%(table_id)s AS temp_reuse_concepts;     
    """


create_values_query = """
    INSERT INTO mapping_scanreportvalue (
        scan_report_field_id, 
        value, 
        frequency, 
        value_description, 
        created_at, 
        updated_at, 
        "conceptID"
    )
    SELECT 
        scan_report_field.id, 
        field_values.value, 
        field_values.frequency, 
        data_dictionary.value_description, 
        NOW(), 
        NOW(), 
        -1
    FROM 
        temp_field_values_%(table_id)s field_values
    JOIN 
        mapping_scanreportfield scan_report_field 
        ON scan_report_field.scan_report_table_id = %(table_id)s 
        AND scan_report_field.name = field_values.field_name
    LEFT JOIN 
        temp_data_dictionary_%(scan_report_id)s data_dictionary
        ON data_dictionary.table_name = %(table_name)s 
        AND data_dictionary.field_name = field_values.field_name
        AND data_dictionary.value = field_values.value
    ORDER BY
        field_values.ctid    -- Keep the order of the values to be the same in the scan report. "ctid": The physical location of the row version within its table.
"""


create_fields_query = """
    INSERT INTO mapping_scanreportfield (
        scan_report_table_id, name, description_column, type_column, created_at, updated_at,
        is_patient_id, is_ignore, pass_from_source
    )
    VALUES (
        %(scan_report_table_id)s, %(name)s, %(description_column)s, %(type_column)s,
        NOW(), NOW(), False, False, True
    )
"""

create_temp_data_dictionary_table_query = """
    CREATE TABLE temp_data_dictionary_%(scan_report_id)s (
        table_name VARCHAR(255),
        field_name VARCHAR(255),
        value TEXT,
        value_description TEXT
    );
"""


create_update_temp_rules_table_query = """
        DROP TABLE IF EXISTS temp_rules_export_%(scan_report_id)s_%(file_type)s;
        CREATE TABLE temp_rules_export_%(scan_report_id)s_%(file_type)s (
            sr_concept_id INT,
            concept_name TEXT,
            concept_id INT,
            dest_field TEXT,
            dest_table TEXT,
            source_field TEXT,
            source_table TEXT,
            term_mapping_value TEXT,
            domain TEXT,
            standard_concept TEXT,
            concept_class TEXT,
            vocabulary TEXT,
            valid_start_date DATE,
            valid_end_date DATE,
            creation_type TEXT
        );
        INSERT INTO temp_rules_export_%(scan_report_id)s_%(file_type)s (
            sr_concept_id,
            concept_name,
            concept_id,
            dest_field,
            dest_table,
            source_field,
            source_table,
            term_mapping_value, 
            creation_type
        )
        SELECT
            mapping_rule.concept_id AS sr_concept_id,
            omop_concept.concept_name,
            sr_concept.concept_id,
            omop_field.field AS dest_field,
            omop_table.table AS dest_table,
            sr_field.name AS source_field,
            sr_table.name AS source_table,
            CASE
                WHEN sr_concept.content_type_id = (
                    SELECT id FROM django_content_type 
                    WHERE app_label = 'mapping' AND model = 'scanreportvalue'
                ) THEN sr_value.value
                ELSE NULL
            END AS term_mapping_value,
            sr_concept.creation_type
        FROM mapping_mappingrule AS mapping_rule
        JOIN mapping_omopfield AS omop_field ON mapping_rule.omop_field_id = omop_field.id
        JOIN mapping_omoptable AS omop_table ON omop_field.table_id = omop_table.id
        JOIN mapping_scanreportfield AS sr_field ON mapping_rule.source_field_id = sr_field.id
        JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
        JOIN mapping_scanreportconcept AS sr_concept ON mapping_rule.concept_id = sr_concept.id
        LEFT JOIN mapping_scanreportvalue AS sr_value ON sr_concept.object_id = sr_value.id AND sr_concept.content_type_id = (
            SELECT id FROM django_content_type 
            WHERE app_label = 'mapping' AND model = 'scanreportvalue'
        )
        LEFT JOIN omop.concept AS omop_concept ON sr_concept.concept_id = omop_concept.concept_id
        WHERE mapping_rule.scan_report_id = %(scan_report_id)s;
"""


create_file_entry_query = """
    INSERT INTO files_filedownload (name, file_url, user_id, file_type_id, scan_report_id, created_at, updated_at)
    VALUES (%(name)s, %(file_url)s, %(user_id)s, %(file_type_id)s, %(scan_report_id)s, %(created_at)s, %(updated_at)s)
"""

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
            sr_concept.content_type_id = 22 
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
            sr_concept.content_type_id = 23 
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
            WHEN temp_table.content_type_id = 22 THEN temp_table.object_id
            WHEN temp_table.content_type_id = 23 THEN (
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
            WHEN sr_field.type_column = 'INT' OR
                sr_field.type_column = 'REAL' OR
                sr_field.type_column = 'FLOAT' OR
                sr_field.type_column = 'NUMERIC' OR
                sr_field.type_column = 'DECIMAL' OR
                sr_field.type_column = 'DOUBLE'
            THEN 'numeric'
            WHEN sr_field.type_column = 'VARCHAR' OR
                sr_field.type_column = 'NVARCHAR' OR
                sr_field.type_column = 'TEXT' OR
                sr_field.type_column = 'STRING' OR
                sr_field.type_column = 'CHAR'
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


find_reusing_value_query = """
INSERT INTO temp_reuse_concepts_%(table_id)s (
    matching_value_name, matching_field_name, matching_table_name, content_type_id, source_concept_id, source_scanreport_id
)
SELECT DISTINCT 
    sr_value.value, 
    sr_field.name,
    sr_table.name,
    23,
    eligible_sr_concept.concept_id,
    -- TODO: add eligible_sr_concept.standard_concept_id here
    eligible_scan_report.id
FROM mapping_scanreportvalue AS sr_value
JOIN mapping_scanreportfield AS sr_field 
    ON sr_value.scan_report_field_id = sr_field.id
JOIN mapping_scanreporttable AS sr_table 
    ON sr_field.scan_report_table_id = %(table_id)s

-- Join to eligible values in other eligible scan reports
JOIN mapping_scanreportvalue AS eligible_sr_value 
    ON sr_value.value = eligible_sr_value.value       -- Matching value's name
    AND (
        sr_value.value_description = eligible_sr_value.value_description
        OR (sr_value.value_description IS NULL AND eligible_sr_value.value_description IS NULL)
    )                                                 -- Matching value's description.
JOIN mapping_scanreportfield AS eligible_sr_field 
    ON eligible_sr_value.scan_report_field_id = eligible_sr_field.id
    AND eligible_sr_field.name = sr_field.name        -- Matching value's field name
JOIN mapping_scanreporttable AS eligible_sr_table 
    ON eligible_sr_field.scan_report_table_id = eligible_sr_table.id
    AND eligible_sr_table.name = sr_table.name        -- Matching table name
JOIN mapping_scanreport AS eligible_scan_report 
    ON eligible_sr_table.scan_report_id = eligible_scan_report.id
    AND eligible_scan_report.id != %(scan_report_id)s -- Don't reuse concepts from the same scan report
JOIN mapping_dataset AS dataset 
    ON eligible_scan_report.parent_dataset_id = dataset.id
JOIN mapping_mappingstatus AS map_status 
    ON eligible_scan_report.mapping_status_id = map_status.id
JOIN mapping_scanreportconcept AS eligible_sr_concept
    ON eligible_sr_concept.object_id = eligible_sr_value.id
    AND eligible_sr_concept.content_type_id = 23     -- Value level concepts
    AND eligible_sr_concept.creation_type != 'R'     -- We don't want to reuse R concepts
    %(exclude_v_concepts_condition)s

WHERE dataset.id = %(parent_dataset_id)s        -- Other conditions
AND dataset.hidden = FALSE
AND eligible_scan_report.hidden = FALSE
AND map_status.value = 'COMPLETE';

-- After finding eligible matching value, we need to delete (matching_value_name, standard_concept_id (future) , source_concept_id) duplicates, 
--only get the occurence with the lowest source_scanreport_id
DELETE FROM temp_reuse_concepts_%(table_id)s AS temp_table
USING temp_reuse_concepts_%(table_id)s AS temp_table_duplicate
WHERE
    temp_table.matching_value_name = temp_table_duplicate.matching_value_name
    AND temp_table.source_concept_id = temp_table_duplicate.source_concept_id
    -- TODO: add standard_concept_id matching check (future) here
    AND temp_table.content_type_id = 23
    AND temp_table.source_scanreport_id > temp_table_duplicate.source_scanreport_id;
"""


find_reusing_field_query = """
INSERT INTO temp_reuse_concepts_%(table_id)s (
    matching_field_name, matching_table_name, content_type_id, source_concept_id, source_scanreport_id
)
SELECT DISTINCT 
    sr_field.name, 
    sr_table.name,
    22,
    eligible_sr_concept.concept_id,
    eligible_scan_report.id
FROM mapping_scanreportfield AS sr_field
JOIN mapping_scanreporttable AS sr_table 
    ON sr_field.scan_report_table_id = %(table_id)s

-- Join to eligible fields in other eligible scan reports
JOIN mapping_scanreportfield AS eligible_sr_field 
    ON eligible_sr_field.name = sr_field.name        -- Matching field name
JOIN mapping_scanreporttable AS eligible_sr_table 
    ON eligible_sr_field.scan_report_table_id = eligible_sr_table.id
    AND eligible_sr_table.name = sr_table.name       -- Matching table name
JOIN mapping_scanreport AS eligible_scan_report 
    ON eligible_sr_table.scan_report_id = eligible_scan_report.id
    AND eligible_scan_report.id != %(scan_report_id)s  -- Don't reuse concepts from the same scan report
JOIN mapping_dataset AS dataset 
    ON eligible_scan_report.parent_dataset_id = dataset.id
JOIN mapping_mappingstatus AS map_status 
    ON eligible_scan_report.mapping_status_id = map_status.id
JOIN mapping_scanreportconcept AS eligible_sr_concept
    ON eligible_sr_concept.object_id = eligible_sr_field.id
    AND eligible_sr_concept.content_type_id = 22     -- Field level concepts
    AND eligible_sr_concept.creation_type != 'R'     -- We don't want to reuse R concepts

WHERE dataset.id = %(parent_dataset_id)s        -- Other conditions
AND dataset.hidden = FALSE
AND eligible_scan_report.hidden = FALSE
AND map_status.value = 'COMPLETE';

-- After finding eligible matching field, we need to delete (matching_field_name, standard_concept_id (future) , source_concept_id) duplicates, 
--only get the occurence with the lowest source_scanreport_id
DELETE FROM temp_reuse_concepts_%(table_id)s AS temp_table
USING temp_reuse_concepts_%(table_id)s AS temp_table_duplicate
WHERE
    temp_table.matching_field_name = temp_table_duplicate.matching_field_name
    AND temp_table.matching_table_name = temp_table_duplicate.matching_table_name
    AND temp_table.source_concept_id = temp_table_duplicate.source_concept_id
    -- TODO: add standard_concept_id matching check (future) here
    AND temp_table.content_type_id = 22
    AND temp_table.source_scanreport_id > temp_table_duplicate.source_scanreport_id;
"""


find_object_id_query = """
    UPDATE temp_reuse_concepts_%(table_id)s AS temp_table
        SET object_id = 
            CASE 
                WHEN temp_table.content_type_id = 22 THEN  -- For ScanReportField
                    (SELECT sr_field.id 
                    FROM mapping_scanreportfield AS sr_field 
                    JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
                    WHERE sr_table.scan_report_id = %(scan_report_id)s AND sr_table.id = %(table_id)s
                    AND sr_field.name = temp_table.matching_field_name
                    AND sr_table.name = temp_table.matching_table_name    -- Matching table name
                    LIMIT 1)
                WHEN temp_table.content_type_id = 23 THEN  -- For ScanReportValue
                    (SELECT sr_value.id 
                    FROM mapping_scanreportvalue AS sr_value
                    JOIN mapping_scanreportfield AS sr_field ON sr_value.scan_report_field_id = sr_field.id
                    JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
                    WHERE sr_table.scan_report_id = %(scan_report_id)s AND sr_table.id = %(table_id)s
                    AND sr_value.value = temp_table.matching_value_name
                    AND sr_field.name = temp_table.matching_field_name    -- Matching field name
                    AND sr_table.name = temp_table.matching_table_name    -- Matching table name
                    LIMIT 1)
                ELSE NULL
            END
        WHERE (temp_table.content_type_id = 22 AND temp_table.matching_field_name IS NOT NULL)
        OR (temp_table.content_type_id = 23 AND temp_table.matching_value_name IS NOT NULL);

    DELETE FROM temp_reuse_concepts_%(table_id)s
    WHERE object_id IS NULL;
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
        scan_report_table_id, name, description_column, type_column,
        max_length, nrows, nrows_checked, fraction_empty,
        nunique_values, fraction_unique, created_at, updated_at,
        is_patient_id, is_ignore, pass_from_source
    )
    VALUES (
        %(scan_report_table_id)s, %(name)s, %(description_column)s, %(type_column)s,
        %(max_length)s, %(nrows)s, %(nrows_checked)s, %(fraction_empty)s,
        %(nunique_values)s, %(fraction_unique)s, NOW(), NOW(), False, False,
        True
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

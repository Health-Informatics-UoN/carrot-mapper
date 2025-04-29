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


def create_temp_reusing_concepts_table(**kwargs):
    """
    Create the temporary table for reusing concepts.
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_R_concepts")
    table_id = validated_params["table_id"]

    # Create the temporary table once, outside the loop, with all the columns needed
    create_table_query = f"""
    DROP TABLE IF EXISTS temp_reuse_concepts_{table_id};
    CREATE TABLE temp_reuse_concepts_{table_id} (
        object_id INTEGER,
        matching_name TEXT,
        source_scanreport_id INTEGER,
        content_type_id INTEGER,
        source_concept_id INTEGER,
        standard_concept_id INTEGER,
        -- TODO: find a better name for this column. This is the field id for the reused concepts in the new SR 
        target_source_field_id INTEGER,
        target_source_field_data_type TEXT,
        sr_concept_id INTEGER,
        dest_table_id INTEGER,
        dest_person_field_id INTEGER,
        dest_date_field_id INTEGER,
        dest_start_date_field_id INTEGER,
        dest_end_date_field_id INTEGER,
        source_concept_field_id INTEGER,
        source_value_field_id INTEGER,
        dest_concept_field_id INTEGER,
        value_as_number_field_id INTEGER,
        value_as_string_field_id INTEGER
    );
    """
    try:
        pg_hook.run(create_table_query)
        logging.info(f"Successfully created temp_standard_concepts_{table_id} table")
    except Exception as e:
        logging.error(
            f"Failed to create temp_standard_concepts_{table_id} table: {str(e)}"
        )
        raise


def find_matching_value(**kwargs):
    """
    Find matching values for reusing concepts.
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_R_concepts")

    parent_dataset_id = validated_params["parent_dataset_id"]
    table_id = validated_params["table_id"]

    # When a data dictionary is provided, we won't reuse V concepts,
    # because that is the job of V concepts DAG
    has_data_dictionary = validated_params["has_data_dictionary"]
    exclude_v_concepts_condition = (
        "AND eligible_sr_concept.creation_type != 'V'" if has_data_dictionary else ""
    )

    find_reusing_value_query = f"""
    INSERT INTO temp_reuse_concepts_{table_id} (
        matching_name, content_type_id, source_concept_id, source_scanreport_id
    )
    SELECT DISTINCT 
        sr_value.value, 
        23,
        eligible_sr_concept.concept_id,
        -- TODO: add eligible_sr_concept.standard_concept_id here
        eligible_scan_report.id
    FROM mapping_scanreportvalue AS sr_value
    JOIN mapping_scanreportfield AS sr_field 
        ON sr_value.scan_report_field_id = sr_field.id
    JOIN mapping_scanreporttable AS sr_table 
        ON sr_field.scan_report_table_id = {table_id}

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
    JOIN mapping_scanreport AS eligible_scan_report 
        ON eligible_sr_table.scan_report_id = eligible_scan_report.id
    JOIN mapping_dataset AS dataset 
        ON eligible_scan_report.parent_dataset_id = dataset.id
    JOIN mapping_mappingstatus AS map_status 
        ON eligible_scan_report.mapping_status_id = map_status.id
    JOIN mapping_scanreportconcept AS eligible_sr_concept
        ON eligible_sr_concept.object_id = eligible_sr_value.id
        AND eligible_sr_concept.content_type_id = 23     -- Value level concepts
        AND eligible_sr_concept.creation_type != 'R'     -- We don't want to reuse R concepts
        {exclude_v_concepts_condition}

    WHERE dataset.id = {parent_dataset_id}        -- Other conditions
    AND dataset.hidden = FALSE
    AND eligible_scan_report.hidden = FALSE
    AND map_status.value = 'COMPLETE';

    -- After finding eligible matching name, we need to delete (matching_name, source_concept_id) duplicates, 
    --only get the occurence with the lowest source_scanreport_id
    DELETE FROM temp_reuse_concepts_{table_id} AS temp_table
    USING temp_reuse_concepts_{table_id} AS temp_table_duplicate
    WHERE
        temp_table.matching_name = temp_table_duplicate.matching_name
        AND temp_table.source_concept_id = temp_table_duplicate.source_concept_id
        AND temp_table.content_type_id = 23
        AND temp_table.source_scanreport_id > temp_table_duplicate.source_scanreport_id;
    """
    try:
        pg_hook.run(find_reusing_value_query)
        logging.info(f"Successfully found reusing concepts at the value level")
    except Exception as e:
        logging.error(f"Failed to find reusing concepts at the value level: {str(e)}")
        raise


def find_matching_field(**kwargs):
    """
    Find matching fields for reusing concepts.
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_R_concepts")

    parent_dataset_id = validated_params["parent_dataset_id"]
    table_id = validated_params["table_id"]

    # When a data dictionary is provided, we won't reuse V concepts,
    # because that is the job of V concepts DAG
    has_data_dictionary = validated_params["has_data_dictionary"]
    exclude_v_concepts_condition = (
        "AND eligible_sr_concept.creation_type != 'V'" if has_data_dictionary else ""
    )

    find_reusing_field_query = f"""
    INSERT INTO temp_reuse_concepts_{table_id} (
        matching_name, content_type_id, source_concept_id, source_scanreport_id
    )
    SELECT DISTINCT 
        sr_field.name, 
        22,
        eligible_sr_concept.concept_id,
        -- TODO: add eligible_sr_concept.standard_concept_id here
        eligible_scan_report.id
    FROM mapping_scanreportfield AS sr_field
    JOIN mapping_scanreporttable AS sr_table 
        ON sr_field.scan_report_table_id = {table_id}

    -- Join to eligible values in other eligible scan reports
    JOIN mapping_scanreportfield AS eligible_sr_field 
        ON eligible_sr_field.name = sr_field.name        -- Matching field name
    JOIN mapping_scanreporttable AS eligible_sr_table 
        ON eligible_sr_field.scan_report_table_id = eligible_sr_table.id
    JOIN mapping_scanreport AS eligible_scan_report 
        ON eligible_sr_table.scan_report_id = eligible_scan_report.id
    JOIN mapping_dataset AS dataset 
        ON eligible_scan_report.parent_dataset_id = dataset.id
    JOIN mapping_mappingstatus AS map_status 
        ON eligible_scan_report.mapping_status_id = map_status.id
    JOIN mapping_scanreportconcept AS eligible_sr_concept
        ON eligible_sr_concept.object_id = eligible_sr_field.id
        AND eligible_sr_concept.content_type_id = 22     -- Field level concepts
        AND eligible_sr_concept.creation_type != 'R'     -- We don't want to reuse R concepts
        {exclude_v_concepts_condition}

    WHERE dataset.id = {parent_dataset_id}        -- Other conditions
    AND dataset.hidden = FALSE
    AND eligible_scan_report.hidden = FALSE
    AND map_status.value = 'COMPLETE';

    -- After finding eligible matching name, we need to delete (matching_name, source_concept_id) duplicates, 
    --only get the occurence with the lowest source_scanreport_id
    DELETE FROM temp_reuse_concepts_{table_id} AS temp_table
    USING temp_reuse_concepts_{table_id} AS temp_table_duplicate
    WHERE
        temp_table.matching_name = temp_table_duplicate.matching_name
        AND temp_table.source_concept_id = temp_table_duplicate.source_concept_id
        AND temp_table.content_type_id = 22
        AND temp_table.source_scanreport_id > temp_table_duplicate.source_scanreport_id;
    """
    try:
        pg_hook.run(find_reusing_field_query)
        logging.info(f"Successfully found reusing concepts at the field level")
    except Exception as e:
        logging.error(f"Failed to find reusing concepts at the value level: {str(e)}")
        raise


def find_object_id(**kwargs):
    """
    Find object ids for reusing concepts.
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_R_concepts")

    scan_report_id = validated_params["scan_report_id"]
    table_id = validated_params["table_id"]

    find_object_id_query = f"""
    UPDATE temp_reuse_concepts_{table_id} AS temp_table
        SET object_id = 
            CASE 
                WHEN temp_table.content_type_id = 22 THEN  -- For ScanReportField
                    (SELECT sr_field.id 
                    FROM mapping_scanreportfield AS sr_field 
                    JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
                    WHERE sr_table.scan_report_id = {scan_report_id} AND sr_table.id = {table_id}
                    AND sr_field.name = temp_table.matching_name
                    LIMIT 1)
                WHEN temp_table.content_type_id = 23 THEN  -- For ScanReportValue
                    (SELECT sr_value.id 
                    FROM mapping_scanreportvalue AS sr_value
                    JOIN mapping_scanreportfield AS sr_field ON sr_value.scan_report_field_id = sr_field.id
                    JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
                    WHERE sr_table.scan_report_id = {scan_report_id} AND sr_table.id = {table_id}
                    AND sr_value.value = temp_table.matching_name
                    LIMIT 1)
                ELSE NULL
            END
        WHERE temp_table.matching_name IS NOT NULL;

        DELETE FROM temp_reuse_concepts_{table_id}
        WHERE object_id IS NULL;
    """
    try:
        pg_hook.run(find_object_id_query)
        logging.info(f"Successfully found object ids for reusing concepts")
    except Exception as e:
        logging.error(f"Failed to find object ids for reusing concepts: {str(e)}")
        raise


def create_reusing_concepts(**kwargs):
    """
    Create standard concepts for field values in the mapping_scanreportconcept table.
    Only inserts concepts that don't already exist.
    """
    try:
        validated_params = pull_validated_params(kwargs, "validate_params_R_concepts")
        table_id = validated_params["table_id"]
        scan_report_id = validated_params["scan_report_id"]

        # TODO: when source_concept_id is added to the model SCANREPORTCONCEPT, we need to update the query belowto solve the issue #1006
        create_concept_query = f"""
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
                temp_reuse_concepts.source_concept_id,
                temp_reuse_concepts.content_type_id -- content_type_id for scanreportvalue
            FROM temp_reuse_concepts_{table_id} AS temp_reuse_concepts
            WHERE NOT EXISTS (
                -- Check if the concept already exists
                SELECT 1 FROM mapping_scanreportconcept AS sr_concept
                WHERE sr_concept.object_id = temp_reuse_concepts.object_id
                -- TODO: if standard_concept_id is null then we need to use the source_concept_id
                AND sr_concept.concept_id = temp_reuse_concepts.source_concept_id
                AND sr_concept.content_type_id = temp_reuse_concepts.content_type_id
            );
            """

        # This is the source field for concepts-related mapping rules created in the next step
        find_target_source_field_id_query = f"""
            -- First set the target_source_field_id
            UPDATE temp_reuse_concepts_{table_id} AS temp_table
            SET target_source_field_id =
                CASE
                    WHEN temp_table.content_type_id = 22 THEN temp_table.object_id
                    WHEN temp_table.content_type_id = 23 THEN (
                        SELECT sr_value.scan_report_field_id
                        FROM mapping_scanreportvalue AS sr_value
                        WHERE sr_value.id = temp_table.object_id
                    )
                    ELSE NULL
                END;

            -- Then use the now-set target_source_field_id to set data type
            UPDATE temp_reuse_concepts_{table_id} AS temp_table
            SET target_source_field_data_type = 
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
            WHERE sr_field.id = temp_table.target_source_field_id
            AND temp_table.target_source_field_id IS NOT NULL;
            """
        try:
            pg_hook.run(create_concept_query + find_target_source_field_id_query)
            logging.info("Successfully created standard concepts")
            # update_job_status(
            #     scan_report=scan_report_id,
            #     scan_report_table=table_id,
            #     stage=JobStageType.REUSE_CONCEPTS,
            #     status=StageStatusType.IN_PROGRESS,
            #     details="Successfully created standard concepts",
            # )
        except Exception as e:
            logging.error(f"Database error in create_standard_concepts: {str(e)}")
            # update_job_status(
            #     scan_report=scan_report_id,
            #     scan_report_table=table_id,
            #     stage=JobStageType.REUSE_CONCEPTS,
            #     status=StageStatusType.FAILED,
            #     details=f"Error in create_standard_concepts: {str(e)}",
            # )
    except Exception as e:
        logging.error(f"Error in create_standard_concepts: {str(e)}")
        raise


def find_sr_concept_id(**kwargs):
    """
    Update temp_standard_concepts table with sr_concept_id column
    containing the IDs of standard concepts added to mapping_scanreportconcept.
    This will help the next steps to be shorter.
    """
    try:
        validated_params = pull_validated_params(kwargs, "validate_params_R_concepts")
        table_id = validated_params["table_id"]

        update_query = f"""        
        -- Update sr_concept_id with the mapping_scanreportconcept ID
        UPDATE temp_reuse_concepts_{table_id} temp_reuse_concepts
        SET sr_concept_id = sr_concept.id
        FROM mapping_scanreportconcept AS sr_concept
        WHERE sr_concept.object_id = temp_reuse_concepts.object_id
        -- TODO: add standard_concept_id here for the newly creted SR concepts
        AND sr_concept.concept_id = temp_reuse_concepts.source_concept_id
        AND sr_concept.content_type_id = temp_reuse_concepts.content_type_id;
        """

        try:
            pg_hook.run(update_query)
            logging.info(
                f"Successfully added sr_concept_id to temp_reuse_concepts_{table_id} table"
            )
        except Exception as e:
            logging.error(f"Database error in find_sr_concept_id: {str(e)}")
            raise
    except Exception as e:
        logging.error(f"Error in find_sr_concept_id: {str(e)}")
        raise

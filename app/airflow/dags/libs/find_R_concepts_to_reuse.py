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


def delete_R_concepts(**kwargs) -> None:
    """
    To make sure the eligble concepts for reusing is up-to-date, we will refresh the R concepts
    by deleting all reused concepts for a given scan report table with creation type 'R' (Reused).
    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    """
    try:
        # Get validated parameters from XCom
        validated_params = pull_validated_params(kwargs, "validate_params")
        table_id = validated_params["table_id"]

        delete_reused_concepts = f"""
            DELETE FROM mapping_scanreportconcept
            WHERE creation_type = 'R' 
            AND (
                -- Delete concepts for fields in this table
                (content_type_id = 22 AND object_id IN (
                    SELECT srf.id 
                    FROM mapping_scanreportfield AS srf
                    WHERE srf.scan_report_table_id = {table_id}
                ))
                OR 
                -- Delete concepts for values in this table
                (content_type_id = 23 AND object_id IN (
                    SELECT srv.id
                    FROM mapping_scanreportvalue AS srv
                    JOIN mapping_scanreportfield AS srf ON srv.scan_report_field_id = srf.id
                    WHERE srf.scan_report_table_id = {table_id}
                ))
            );
        """
        pg_hook.run(delete_reused_concepts)

    except Exception as e:
        logging.error(f"Error in delete_mapping_rules: {str(e)}")
        raise


def find_matching_value(**kwargs):
    """
    Identifies and extracts field values from completed scan reports that can be reused for concept mapping.

    This function locates field values in the current table that match values in previously mapped scan reports
    within the same parent dataset. The matching process requires:
    1. Exact value text matching
    2. Matching value descriptions (or both NULL)
    3. Values must belong to fields with the same name

    The SQL procedure:
    1. Starts with values in the current scan report table
    2. Joins to values in other scan reports based on value name, description, and field name
    3. Finds values with associated concepts in completed scan reports
    4. Filters to values from the specified parent dataset and only from completed scan reports
    5. Excludes already reused concepts (creation_type != 'R')
    6. Optionally excludes concepts from vocabulary matching (creation_type != 'V') if a data dictionary exists
    7. Removes duplicate matches, keeping only the match from the oldest scan report

    Results are stored in a temporary table (temp_reuse_concepts_{table_id}) for further processing.

    Required parameters (pulled from XCom):
        - table_id (int): ID of the scan report table being processed
        - parent_dataset_id (int): ID of the parent dataset to search within
        - scan_report_id (int): ID of the current scan report
        - has_data_dictionary (bool): If True, V-type concepts will be excluded from reuse
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params")

    parent_dataset_id = validated_params["parent_dataset_id"]
    table_id = validated_params["table_id"]
    scan_report_id = validated_params["scan_report_id"]

    update_job_status(
        scan_report=scan_report_id,
        scan_report_table=table_id,
        stage=JobStageType.REUSE_CONCEPTS,
        status=StageStatusType.IN_PROGRESS,
        details=f"Finding eligible concepts for reuse at the value level",
    )

    # Create temp table for reuse concepts
    create_table_query = f"""
    CREATE TABLE temp_reuse_concepts_{table_id} (
        object_id INTEGER,
        matching_value_name TEXT,
        matching_field_name TEXT,
        matching_table_name TEXT,
        -- TODO: we need to add source_scanreport_id for the model SCANREPORTCONCEPT as well for R concepts
        source_scanreport_id INTEGER,
        content_type_id INTEGER,
        source_concept_id INTEGER,
        standard_concept_id INTEGER
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

    # When a data dictionary (or field_vocab_pairs) for a table is provided, we won't reuse V concepts,
    # because that is the job of V concepts DAG
    field_vocab_pairs = validated_params["field_vocab_pairs"]
    exclude_v_concepts_condition = (
        "AND eligible_sr_concept.creation_type != 'V'" if field_vocab_pairs else ""
    )

    find_reusing_value_query = f"""
    INSERT INTO temp_reuse_concepts_{table_id} (
        matching_value_name, matching_field_name, content_type_id, source_concept_id, source_scanreport_id
    )
    SELECT DISTINCT 
        sr_value.value, 
        sr_field.name,
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

    -- After finding eligible matching value, we need to delete (matching_value_name, source_concept_id) duplicates, 
    --only get the occurence with the lowest source_scanreport_id
    DELETE FROM temp_reuse_concepts_{table_id} AS temp_table
    USING temp_reuse_concepts_{table_id} AS temp_table_duplicate
    WHERE
        temp_table.matching_value_name = temp_table_duplicate.matching_value_name
        AND temp_table.source_concept_id = temp_table_duplicate.source_concept_id
        AND temp_table.content_type_id = 23
        AND temp_table.source_scanreport_id > temp_table_duplicate.source_scanreport_id;
    """
    try:
        pg_hook.run(find_reusing_value_query)
        logging.info(f"Successfully found reusing concepts at the value level")
    except Exception as e:
        logging.error(f"Failed to find reusing concepts at the value level: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.REUSE_CONCEPTS,
            status=StageStatusType.FAILED,
            details=f"Error when finding eligible concepts for reuse at the value level",
        )
        raise


def find_matching_field(**kwargs):
    """
    Finds matching fields in previously completed scan reports that can be reused for concept mapping.

    This function identifies fields in the current table that match fields in other scan reports
    which already have concepts assigned. It identifies matching fields by name and inserts them
    into the temporary reuse concepts table for later processing.

    The function prioritizes concepts from the oldest scan report when duplicates are found.

    Required parameters (pulled from XCom):
        - table_id (int): ID of the scan report table being processed
        - parent_dataset_id (int): ID of the parent dataset to search within
        - scan_report_id (int): ID of the current scan report
        - has_data_dictionary (bool): If True, V-type concepts will be excluded from reuse
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params")

    parent_dataset_id = validated_params["parent_dataset_id"]
    table_id = validated_params["table_id"]
    scan_report_id = validated_params["scan_report_id"]

    update_job_status(
        scan_report=scan_report_id,
        scan_report_table=table_id,
        stage=JobStageType.REUSE_CONCEPTS,
        status=StageStatusType.IN_PROGRESS,
        details=f"Finding eligible concepts for reuse at the field level",
    )

    find_reusing_field_query = f"""
    INSERT INTO temp_reuse_concepts_{table_id} (
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
        ON sr_field.scan_report_table_id = {table_id}

    -- Join to eligible fields in other eligible scan reports
    JOIN mapping_scanreportfield AS eligible_sr_field 
        ON eligible_sr_field.name = sr_field.name        -- Matching field name
    JOIN mapping_scanreporttable AS eligible_sr_table 
        ON eligible_sr_field.scan_report_table_id = eligible_sr_table.id
        AND eligible_sr_table.name = sr_table.name       -- Matching table name
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

    WHERE dataset.id = {parent_dataset_id}        -- Other conditions
    AND dataset.hidden = FALSE
    AND eligible_scan_report.hidden = FALSE
    AND map_status.value = 'COMPLETE';

    -- After finding eligible matching field, we need to delete (matching_field_name, source_concept_id) duplicates, 
    --only get the occurence with the lowest source_scanreport_id
    DELETE FROM temp_reuse_concepts_{table_id} AS temp_table
    USING temp_reuse_concepts_{table_id} AS temp_table_duplicate
    WHERE
        temp_table.matching_field_name = temp_table_duplicate.matching_field_name
        AND temp_table.matching_table_name = temp_table_duplicate.matching_table_name
        AND temp_table.source_concept_id = temp_table_duplicate.source_concept_id
        AND temp_table.content_type_id = 22
        AND temp_table.source_scanreport_id > temp_table_duplicate.source_scanreport_id;
    """
    try:
        pg_hook.run(find_reusing_field_query)
        logging.info(f"Successfully found reusing concepts at the field level")
    except Exception as e:
        logging.error(f"Failed to find reusing concepts at the value level: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.REUSE_CONCEPTS,
            status=StageStatusType.FAILED,
            details=f"Error when finding eligible concepts for reuse at the field level",
        )
        raise


def find_object_id(**kwargs):
    """
    Find object ids for reusing concepts.
    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    - scan_report_id (int): The ID of the scan report to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params")

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
                        AND sr_field.name = temp_table.matching_field_name
                        AND sr_table.name = temp_table.matching_table_name
                        LIMIT 1)
                    WHEN temp_table.content_type_id = 23 THEN  -- For ScanReportValue
                        (SELECT sr_value.id 
                        FROM mapping_scanreportvalue AS sr_value
                        JOIN mapping_scanreportfield AS sr_field ON sr_value.scan_report_field_id = sr_field.id
                        JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
                        WHERE sr_table.scan_report_id = {scan_report_id} AND sr_table.id = {table_id}
                        AND sr_value.value = temp_table.matching_value_name
                        AND sr_field.name = temp_table.matching_field_name
                        LIMIT 1)
                    ELSE NULL
                END
            WHERE (temp_table.content_type_id = 22 AND temp_table.matching_field_name IS NOT NULL)
            OR (temp_table.content_type_id = 23 AND temp_table.matching_value_name IS NOT NULL);

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
    Create R concepts for a given scan report table.
    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    - scan_report_id (int): The ID of the scan report to process
    """

    validated_params = pull_validated_params(kwargs, "validate_params")
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
        FROM temp_reuse_concepts_{table_id} AS temp_reuse_concepts;

        -- Drop the temp table holding the temp reusing concepts data after creating the R concepts
        DROP TABLE IF EXISTS temp_reuse_concepts_{table_id};
        """

    try:
        pg_hook.run(create_concept_query)
        logging.info("Successfully created R (Reused) concepts")
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.REUSE_CONCEPTS,
            status=StageStatusType.COMPLETE,
            details="R (Reused) concepts successfully created from matching fields and values",
        )
    except Exception as e:
        logging.error(f"Database error in create_standard_concepts: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.REUSE_CONCEPTS,
            status=StageStatusType.FAILED,
            details=f"Error when creating R (Reused) concepts",
        )
        raise

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


def delete_mapping_rules(**kwargs) -> None:
    """
    Delete all mapping rules for a given scan report table.
    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params")
    table_id = validated_params["table_id"]
    try:
        delete_query = f"""
        DELETE FROM mapping_mappingrule
        WHERE source_field_id IN (
            SELECT id FROM mapping_scanreportfield
            WHERE scan_report_table_id = {table_id}
        );
        """
        pg_hook.run(delete_query)
    except Exception as e:
        logging.error(f"Error in delete_mapping_rules: {str(e)}")
        raise ValueError(f"Error in delete_mapping_rules: {str(e)}")


def create_temp_existing_concepts_table(**kwargs) -> None:
    """
    Create the temporary table for all existing concepts.
    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params")
    table_id = validated_params["table_id"]

    # Create the temporary table once, outside the loop, with all the columns needed
    create_table_query = f"""
    DROP TABLE IF EXISTS temp_existing_concepts_{table_id};
    CREATE TABLE temp_existing_concepts_{table_id} (
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
    try:
        pg_hook.run(create_table_query)
        logging.info(f"Successfully created temp_standard_concepts_{table_id} table")
    except Exception as e:
        logging.error(
            f"Failed to create temp_standard_concepts_{table_id} table: {str(e)}"
        )
        raise


def find_existing_concepts(**kwargs) -> None:
    """
    Find all existing concepts for a given scan report table.
    Validated param needed is:
    - table_id (int): The ID of the scan report table to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params")

    table_id = validated_params["table_id"]
    scan_report_id = validated_params["scan_report_id"]

    update_job_status(
        scan_report=scan_report_id,
        scan_report_table=table_id,
        stage=JobStageType.GENERATE_RULES,
        status=StageStatusType.IN_PROGRESS,
        details=f"Retrieving all existing concepts in the scan report table",
    )

    find_existing_concepts_query = f"""
        INSERT INTO temp_existing_concepts_{table_id} (
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
                    WHERE sr_table.scan_report_id = {scan_report_id} AND sr_table.id = {table_id}
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
                    WHERE sr_table.scan_report_id = {scan_report_id} AND sr_table.id = {table_id}
                )
            );
            """

    # This is the source field for concepts-related mapping rules created in the next step
    find_source_field_id_query = f"""
        -- First set the source_field_id
        UPDATE temp_existing_concepts_{table_id} AS temp_table
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
        UPDATE temp_existing_concepts_{table_id} AS temp_table
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
    try:
        pg_hook.run(find_existing_concepts_query + find_source_field_id_query)
        logging.info(f"Successfully found existing concepts")
    except Exception as e:
        logging.error(f"Failed to find existing concepts: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.GENERATE_RULES,
            status=StageStatusType.FAILED,
            details=f"Error when finding existing concepts",
        )
        raise

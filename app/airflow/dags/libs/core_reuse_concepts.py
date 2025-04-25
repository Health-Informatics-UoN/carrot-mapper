from libs.utils import (
    process_field_vocab_pairs,
    update_job_status,
    JobStageType,
    StageStatusType,
)
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def find_eligible_objects(**kwargs):
    """
    Find eligible objects for reuse concepts.
    """
    try:
        scan_report_id = kwargs.get("dag_run", {}).conf.get("scan_report_id")
        parent_dataset_id = kwargs.get("dag_run", {}).conf.get("parent_dataset_id")
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")

        # Insert data for each field-vocabulary pair
        find_eligible_objects_query = f"""
        INSERT INTO temp_reuse_concepts_{table_id} (source_concept_id, source_object_id, content_type_id, source_scanreport_id)
        SELECT 
            sr_concept.concept_id,
            sr_concept.object_id,
            sr_concept.content_type_id,
            scan_report.id
        FROM 
            mapping_scanreportconcept AS sr_concept
        JOIN 
            mapping_scanreport AS scan_report ON 
                -- This join depends on the content_type
                CASE 
                    WHEN sr_concept.content_type_id = 23 THEN  -- For ScanReportValue
                        EXISTS (
                            SELECT 1 FROM mapping_scanreportvalue AS sr_value
                            JOIN mapping_scanreportfield AS sr_field ON sr_value.scan_report_field_id = sr_field.id
                            JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
                            WHERE sr_value.id = sr_concept.object_id AND sr_table.scan_report_id = scan_report.id
                        )
                    WHEN sr_concept.content_type_id = 22 THEN  -- For ScanReportField
                        EXISTS (
                            SELECT 1 FROM mapping_scanreportfield AS sr_field
                            JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
                            WHERE sr_field.id = sr_concept.object_id AND sr_table.scan_report_id = scan_report.id
                        )
                    ELSE FALSE
                END
        JOIN 
            mapping_dataset AS dataset ON scan_report.parent_dataset_id = dataset.id
        JOIN 
            mapping_mappingstatus AS mapping_status ON scan_report.mapping_status_id = mapping_status.id
        WHERE 
            dataset.id = {parent_dataset_id}
            AND dataset.visibility = 'PUBLIC'
            AND scan_report.visibility = 'PUBLIC'
            AND mapping_status.value = 'COMPLETE'
            AND sr_concept.creation_type != 'R'
        ORDER BY 
            sr_concept.id;

        UPDATE temp_reuse_concepts_{table_id} temp_reuse_concepts
        SET matching_name = 
            CASE 
                WHEN temp_reuse_concepts.content_type_id = 22 THEN  -- For ScanReportField
                    (SELECT sr_field.name 
                    FROM mapping_scanreportfield AS sr_field 
                    WHERE sr_field.id = temp_reuse_concepts.source_object_id)
                WHEN temp_reuse_concepts.content_type_id = 23 THEN  -- For ScanReportValue
                    (SELECT sr_value.value 
                    FROM mapping_scanreportvalue AS sr_value 
                    WHERE sr_value.id = temp_reuse_concepts.source_object_id)
                ELSE NULL
            END
        WHERE temp_reuse_concepts.source_object_id IS NOT NULL;
        


        UPDATE temp_reuse_concepts_{table_id} temp_reuse_concepts
        SET object_id = 
            CASE 
                WHEN temp_reuse_concepts.content_type_id = 22 THEN  -- For ScanReportField
                    (SELECT sr_field.id 
                    FROM mapping_scanreportfield AS sr_field 
                    JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
                    WHERE sr_table.scan_report_id = {scan_report_id} AND sr_table.id = {table_id}
                    AND sr_field.name = temp_reuse_concepts.matching_name
                    LIMIT 1)
                WHEN temp_reuse_concepts.content_type_id = 23 THEN  -- For ScanReportValue
                    (SELECT sr_value.id 
                    FROM mapping_scanreportvalue AS sr_value
                    JOIN mapping_scanreportfield AS sr_field ON sr_value.scan_report_field_id = sr_field.id
                    JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
                    WHERE sr_table.scan_report_id = {scan_report_id} AND sr_table.id = {table_id}
                    AND sr_value.value = temp_reuse_concepts.matching_name
                    LIMIT 1)
                ELSE NULL
            END
        WHERE temp_reuse_concepts.matching_name IS NOT NULL;

        DELETE FROM temp_reuse_concepts_{table_id}
        WHERE object_id IS NULL;
        """
        try:
            pg_hook.run(find_eligible_objects_query)
            logging.info(
                f"Successfully inserted eligible objects for table ID {table_id}"
            )
        except Exception as e:
            logging.error(
                f"Failed to insert eligible objects for table ID {table_id}: {str(e)}"
            )
            # update_job_status(
            #     scan_report_id=scan_report_id,
            #     table_id=table_id,
            #     stage=JobStageType.REUSE_CONCEPTS,
            #     status=StageStatusType.FAILED,
            #     details=f"Error in find_eligible_objects_query: {str(e)}",
            # )
            raise
    except Exception as e:
        logging.error(f"Error in find_eligible_objects: {str(e)}")
        raise


def create_temp_reusing_concepts_table(**kwargs):
    """
    Create the temporary table for reusing concepts.
    """

    table_id = kwargs.get("dag_run", {}).conf.get("table_id")

    # Create the temporary table once, outside the loop, with all the columns needed
    create_table_query = f"""
    DROP TABLE IF EXISTS temp_reuse_concepts_{table_id};
    CREATE TABLE temp_reuse_concepts_{table_id} (
        object_id INTEGER,
        matching_name TEXT,
        source_object_id INTEGER,
        source_scanreport_id INTEGER,
        content_type_id INTEGER,
        source_concept_id INTEGER,
        standard_concept_id INTEGER,
        source_field_id INTEGER,
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


def find_reusing_value(**kwargs):
    """
    Find reusing concepts at the value level.
    """

    parent_dataset_id = kwargs.get("dag_run", {}).conf.get("parent_dataset_id")
    table_id = kwargs.get("dag_run", {}).conf.get("table_id")

    find_reusing_value_query = f"""
    INSERT INTO temp_reuse_concepts_{table_id} (
        matching_name, content_type_id, source_object_id, source_concept_id, source_scanreport_id
    )
    SELECT DISTINCT 
        sr_value.value, 
        23,
        eligible_sr_value.id,
        eligible_sr_concept.concept_id,
        eligible_scan_report.id
    FROM mapping_scanreportvalue AS sr_value
    JOIN mapping_scanreportfield AS sr_field 
        ON sr_value.scan_report_field_id = sr_field.id
    JOIN mapping_scanreporttable AS sr_table 
        ON sr_field.scan_report_table_id = sr_table.id

    -- Join to eligible values in other eligible scan reports
    JOIN mapping_scanreportvalue AS eligible_sr_value 
        ON sr_value.value = eligible_sr_value.value
    JOIN mapping_scanreportfield AS eligible_sr_field 
        ON eligible_sr_value.scan_report_field_id = eligible_sr_field.id
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
        AND eligible_sr_concept.content_type_id = 23
        AND eligible_sr_concept.creation_type != 'R'

    WHERE dataset.id = {parent_dataset_id}
    AND dataset.hidden = FALSE
    AND eligible_scan_report.hidden = FALSE
    AND map_status.value = 'COMPLETE';
    """

    # TODO: find a way to drop duplicated pair (object - source_concept_id - standard_concept_id)
    #    DELETE FROM temp_reuse_concepts_{table_id}
    # WHERE matching_name IN (
    #     SELECT matching_name FROM temp_reuse_concepts_{table_id}
    #     GROUP BY matching_name, source_concept_id
    #     HAVING COUNT(*) > 1
    # );

    try:
        pg_hook.run(find_reusing_value_query)
        logging.info(f"Successfully found reusing concepts at the value level")
    except Exception as e:
        logging.error(f"Failed to find reusing concepts at the value level: {str(e)}")
        raise


def create_reusing_concepts(**kwargs):
    """
    Create standard concepts for field values in the mapping_scanreportconcept table.
    Only inserts concepts that don't already exist.
    """
    try:
        scan_report_id = kwargs.get("dag_run", {}).conf.get("scan_report_id")
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")

        if not table_id:
            logging.warning("No table_id provided in create_standard_concepts")
        # TODO: when source_concept_id is added to the model SCANREPORTCONCEPT, we need to update the query belowto solve the issue #1006
        create_concept_query = f"""
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
                temp_reuse_concepts.sr_value_id,
                'R',       -- Creation type: Reused
                temp_reuse_concepts.standard_concept_id,
                temp_reuse_concepts.content_type_id -- content_type_id for scanreportvalue
            FROM temp_reuse_concepts_{table_id} AS temp_reuse_concepts
            WHERE NOT EXISTS (
                -- Check if the concept already exists
                SELECT 1 FROM mapping_scanreportconcept AS sr_concept
                WHERE sr_concept.object_id = temp_reuse_concepts.sr_value_id
                AND sr_concept.concept_id = temp_reuse_concepts.standard_concept_id
                AND sr_concept.content_type_id = temp_reuse_concepts.content_type_id
            );
            """
        try:
            pg_hook.run(create_concept_query)
            logging.info("Successfully created standard concepts")
            update_job_status(
                scan_report_id=scan_report_id,
                table_id=table_id,
                stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
                status=StageStatusType.COMPLETE,
                details="Successfully created standard concepts",
            )
        except Exception as e:
            logging.error(f"Database error in create_standard_concepts: {str(e)}")
            update_job_status(
                scan_report_id=scan_report_id,
                table_id=table_id,
                stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
                status=StageStatusType.FAILED,
                details=f"Error in create_standard_concepts: {str(e)}",
            )
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
        table_id = kwargs.get("dag_run", {}).conf.get("table_id")

        if not table_id:
            logging.warning("No table_id provided in find_sr_concept_id")

        update_query = f"""        
        -- Update sr_concept_id with the mapping_scanreportconcept ID
        UPDATE temp_standard_concepts_{table_id} temp_reuse_concepts
        SET sr_concept_id = sr_concept.id
        FROM mapping_scanreportconcept sr_concept
        WHERE sr_concept.object_id = temp_reuse_concepts.sr_value_id
        AND sr_concept.concept_id = temp_reuse_concepts.standard_concept_id
        AND sr_concept.content_type_id = 23;
        """

        try:
            pg_hook.run(update_query)
            logging.info(
                f"Successfully added sr_concept_id to temp_standard_concepts_{table_id} table"
            )
        except Exception as e:
            logging.error(f"Database error in find_sr_concept_id: {str(e)}")
            raise
    except Exception as e:
        logging.error(f"Error in find_sr_concept_id: {str(e)}")
        raise

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
            logging.info(
                f"Successfully created temp_standard_concepts_{table_id} table"
            )
        except Exception as e:
            logging.error(
                f"Failed to create temp_standard_concepts_{table_id} table: {str(e)}"
            )
            raise

        # update_job_status(
        #     scan_report_id=scan_report_id,
        #     table_id=table_id,
        #     stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
        #     status=StageStatusType.IN_PROGRESS,
        #     details=f"Finding eligible objects for table ID {table_id}",
        # )
        # Insert data for each field-vocabulary pair
        find_eligible_objects_query = f"""
        INSERT INTO temp_reuse_concepts_{table_id} (source_concept_id, source_object_id, content_type_id, source_scanreport_id)
        SELECT 
            src.concept_id,
            src.object_id,
            src.content_type_id,
            sr.id
        FROM 
            mapping_scanreportconcept src
        JOIN 
            mapping_scanreport sr ON 
                -- This join depends on the content_type
                CASE 
                    WHEN src.content_type_id = 23 THEN  -- For ScanReportValue
                        EXISTS (
                            SELECT 1 FROM mapping_scanreportvalue srv
                            JOIN mapping_scanreportfield srf ON srv.scan_report_field_id = srf.id
                            JOIN mapping_scanreporttable srt ON srf.scan_report_table_id = srt.id
                            WHERE srv.id = src.object_id AND srt.scan_report_id = sr.id
                        )
                    WHEN src.content_type_id = 22 THEN  -- For ScanReportField
                        EXISTS (
                            SELECT 1 FROM mapping_scanreportfield srf
                            JOIN mapping_scanreporttable srt ON srf.scan_report_table_id = srt.id
                            WHERE srf.id = src.object_id AND srt.scan_report_id = sr.id
                        )
                    ELSE FALSE
                END
        JOIN 
            mapping_dataset ds ON sr.parent_dataset_id = ds.id
        JOIN 
            mapping_mappingstatus ms ON sr.mapping_status_id = ms.id
        WHERE 
            ds.id = {parent_dataset_id}
            AND ds.visibility = 'PUBLIC'
            AND sr.visibility = 'PUBLIC'
            AND ms.value = 'COMPLETE'
            AND src.creation_type != 'R'
        ORDER BY 
            src.id;

        UPDATE temp_reuse_concepts_{table_id} trc
        SET matching_name = 
            CASE 
                WHEN trc.content_type_id = 22 THEN  -- For ScanReportField
                    (SELECT srf.name 
                    FROM mapping_scanreportfield srf 
                    WHERE srf.id = trc.source_object_id)
                WHEN trc.content_type_id = 23 THEN  -- For ScanReportValue
                    (SELECT srv.value 
                    FROM mapping_scanreportvalue srv 
                    WHERE srv.id = trc.source_object_id)
                ELSE NULL
            END
        WHERE trc.source_object_id IS NOT NULL;
        


        UPDATE temp_reuse_concepts_{table_id} trc
        SET object_id = 
            CASE 
                WHEN trc.content_type_id = 22 THEN  -- For ScanReportField
                    (SELECT srf.id 
                    FROM mapping_scanreportfield srf 
                    JOIN mapping_scanreporttable srt ON srf.scan_report_table_id = srt.id
                    WHERE srt.scan_report_id = {scan_report_id} AND srt.id = {table_id}
                    AND srf.name = trc.matching_name
                    LIMIT 1)
                WHEN trc.content_type_id = 23 THEN  -- For ScanReportValue
                    (SELECT srv.id 
                    FROM mapping_scanreportvalue srv
                    JOIN mapping_scanreportfield srf ON srv.scan_report_field_id = srf.id
                    JOIN mapping_scanreporttable srt ON srf.scan_report_table_id = srt.id
                    WHERE srt.scan_report_id = {scan_report_id} AND srt.id = {table_id}
                    AND srv.value = trc.matching_name
                    LIMIT 1)
                ELSE NULL
            END
        WHERE trc.matching_name IS NOT NULL;

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
                tsc.sr_value_id,
                'R', -- Creation type: Built from Vocab dict
                tsc.standard_concept_id,
                tsc.content_type_id -- content_type_id for scanreportvalue
            FROM temp_reuse_concepts_{table_id} tsc
            WHERE NOT EXISTS (
                -- Check if the concept already exists
                SELECT 1 FROM mapping_scanreportconcept
                WHERE object_id = tsc.sr_value_id
                AND concept_id = tsc.standard_concept_id
                AND content_type_id = tsc.content_type_id
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
        UPDATE temp_standard_concepts_{table_id} tsc
        SET sr_concept_id = src.id
        FROM mapping_scanreportconcept src
        WHERE src.object_id = tsc.sr_value_id
        AND src.concept_id = tsc.standard_concept_id
        AND src.content_type_id = 23;
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

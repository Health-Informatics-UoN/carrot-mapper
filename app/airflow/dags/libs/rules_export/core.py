import logging
import os
from openpyxl import load_workbook
from libs.utils import pull_validated_params
import csv
from io import StringIO
from libs.SR_processing.db_services import (
    create_field_entries,
    update_temp_data_dictionary_table,
    create_temp_field_values_table,
    delete_temp_tables,
)
from libs.SR_processing.helpers import (
    remove_BOM,
    process_four_item_dict,
    get_unique_table_names,
    download_blob_to_tmp,
    transform_scan_report_sheet_table,
)
from airflow.providers.postgres.hooks.postgres import PostgresHook
from typing import List, Tuple
from libs.queries import create_values_query, create_temp_data_dictionary_table_query
from libs.enums import JobStageType, StageStatusType
from libs.utils import update_job_status

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def process_rules_export(**kwargs) -> None:
    """
    Wrapper function for the rules export processing task using openpyxl

    Args:
        context: Airflow context containing task information

    Returns:
        None
    """

    validated_params = pull_validated_params(kwargs, "validate_params_rules_export")
    scan_report_id = validated_params["scan_report_id"]
    user_id = validated_params["user_id"]
    file_type = validated_params["file_type"]

    create_temp_rules_table_query = """
        DROP TABLE IF EXISTS temp_rules_export_%(scan_report_id)s;
        CREATE TABLE temp_rules_export_%(scan_report_id)s (
            sr_concept_id INT,
            concept_name TEXT,
            concept_id INT,
            dest_field TEXT,
            dest_table TEXT,
            source_field TEXT,
            source_table TEXT,
            term_mapping_value TEXT
        );
        INSERT INTO temp_rules_export_%(scan_report_id)s (
            sr_concept_id,
            concept_name,
            concept_id,
            dest_field,
            dest_table,
            source_field,
            source_table,
            term_mapping_value
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
                WHEN sr_concept.content_type_id = 23 THEN sr_value.value
                ELSE NULL
            END AS term_mapping_value
        FROM mapping_mappingrule AS mapping_rule
        JOIN mapping_omopfield AS omop_field ON mapping_rule.omop_field_id = omop_field.id
        JOIN mapping_omoptable AS omop_table ON omop_field.table_id = omop_table.id
        JOIN mapping_scanreportfield AS sr_field ON mapping_rule.source_field_id = sr_field.id
        JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
        JOIN mapping_scanreportconcept AS sr_concept ON mapping_rule.concept_id = sr_concept.id
        LEFT JOIN mapping_scanreportvalue AS sr_value ON sr_concept.object_id = sr_value.id AND sr_concept.content_type_id = 23
        LEFT JOIN omop.concept AS omop_concept ON sr_concept.concept_id = omop_concept.concept_id
        WHERE mapping_rule.scan_report_id = %(scan_report_id)s;
    """

    pg_hook.run(
        create_temp_rules_table_query, parameters={"scan_report_id": scan_report_id}
    )


def process_and_create_scan_report_entries(**kwargs) -> None:
    """
    Processes the scan report and creates the scan report entries in the database.
    Steps:
    1. Get the unique table names from the worksheet
    2. Create Scan Report Tables and get table name and id pairs
    3. Create a temporary table to store the field values and their frequencies
    4. Create fields based on the table pairs in the last step
    5. Create scan report values using temporary tables: data_dictionary and field_values, based on the table pairs

    Args:
        context: Airflow context containing task information

    Returns:
        None
    """

    validated_params = pull_validated_params(kwargs, "validate_params_SR_processing")
    scan_report_id = validated_params["scan_report_id"]
    scan_report_blob = validated_params["scan_report_blob"]
    # Read and process the Excel file
    local_SR_path = download_blob_to_tmp(
        container_name="scan-reports", blob_name=scan_report_blob
    )
    logging.info(f"Reading file from {local_SR_path}")
    workbook = load_workbook(
        filename=local_SR_path, data_only=True, keep_links=False, read_only=True
    )

    worksheet = workbook.worksheets[0]
    # Get the unique table names from the worksheet
    table_names = get_unique_table_names(worksheet)
    # Initialise a list to store the table name and id pairs
    table_pairs: List[Tuple[str, int]] = []

    if table_names:
        try:
            # Prepare and execute each insert with RETURNING id to build table name and id pairs
            insert_sql = """
                INSERT INTO mapping_scanreporttable (scan_report_id, name, created_at, updated_at)
                VALUES (%(scan_report_id)s, %(table_name)s, NOW(), NOW())
                RETURNING id
            """

            for table_name in table_names:
                result = pg_hook.get_records(
                    insert_sql,
                    parameters={
                        "scan_report_id": scan_report_id,
                        "table_name": table_name,
                    },
                )
                # Extract the id from the returned record
                table_id = result[0][0]
                table_pairs.append((table_name, table_id))
                # Generate a dictionary of field name - values and their frequencies
                field_values_dict = transform_scan_report_sheet_table(
                    workbook[table_name]
                )
                # Create a temporary table to store the field values and their frequencies
                create_temp_field_values_table(field_values_dict, table_id)

        except Exception as e:
            logging.error(
                f"Error inserting tables into mapping_scanreporttable: {str(e)}"
            )
            update_job_status(
                stage=JobStageType.UPLOAD_SCAN_REPORT,
                status=StageStatusType.FAILED,
                scan_report=scan_report_id,
            )
            raise e

        # Create fields based on the table pairs in the last step
        try:
            create_field_entries(worksheet, table_pairs)
            logging.info("Created scan report fields")

        except Exception as e:
            logging.error(f"Error creating scan report fields: {str(e)}")
            update_job_status(
                stage=JobStageType.UPLOAD_SCAN_REPORT,
                status=StageStatusType.FAILED,
                scan_report=scan_report_id,
            )
            raise e

        # Create scan report values using temporary tables: data_dictionary and field_values, based on the table pairs
        try:
            for table_name, table_id in table_pairs:
                # Insert scan report values using data from temporary tables
                pg_hook.run(
                    create_values_query,
                    parameters={
                        "table_id": table_id,
                        "table_name": table_name,
                        "scan_report_id": scan_report_id,
                    },
                )
        except Exception as e:
            logging.error(f"Error creating scan report values: {str(e)}")
            update_job_status(
                stage=JobStageType.UPLOAD_SCAN_REPORT,
                status=StageStatusType.FAILED,
                scan_report=scan_report_id,
            )
            raise e

        # Delete the temporary tables after processing and creating the scan report values/fields/tables
        delete_temp_tables(scan_report_id, table_pairs)
    else:
        logging.info("No tables found in the scan report, skipping processing")
        update_job_status(
            stage=JobStageType.UPLOAD_SCAN_REPORT,
            status=StageStatusType.FAILED,
            scan_report=scan_report_id,
        )
    # Remove the temp file after processing
    # TODO: double check with KubernetesExecutor if this is the best way to do this
    os.remove(local_SR_path)
    update_job_status(
        stage=JobStageType.UPLOAD_SCAN_REPORT,
        status=StageStatusType.COMPLETE,
        scan_report=scan_report_id,
    )

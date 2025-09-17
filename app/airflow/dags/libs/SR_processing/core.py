import csv
import logging
import os
from io import StringIO
from typing import List, Tuple

from airflow.providers.postgres.hooks.postgres import PostgresHook
from libs.enums import JobStageType, StageStatusType
from libs.queries import create_temp_data_dictionary_table_query, create_values_query
from libs.settings import AIRFLOW_DAGRUN_TIMEOUT
from libs.SR_processing.db_services import (
    create_field_entries,
    create_temp_field_values_table,
    delete_temp_tables,
    update_temp_data_dictionary_table,
)
from libs.SR_processing.helpers import (
    get_unique_table_names,
    process_four_item_dict,
    remove_BOM,
    transform_scan_report_sheet_table,
)
from libs.storage_services import download_blob_to_tmp
from libs.utils import pull_validated_params, update_job_status
from openpyxl import load_workbook

# PostgreSQL connection hook
pg_hook = PostgresHook(
    postgres_conn_id="postgres_db_conn",
    options=f"-c statement_timeout={float(AIRFLOW_DAGRUN_TIMEOUT) * 60 * 1000}ms",
)


def process_data_dictionary(**kwargs) -> None:
    """
    Wrapper function for the data dictionary processing task using openpyxl

    Args:
        context: Airflow context containing task information

    Returns:
        None
    """

    validated_params = pull_validated_params(kwargs, "validate_params_SR_processing")
    scan_report_id = validated_params["scan_report_id"]
    data_dictionary_blob = validated_params["data_dictionary_blob"]
    # Create a temporary table to store the data dictionary
    pg_hook.run(
        create_temp_data_dictionary_table_query,
        parameters={"scan_report_id": scan_report_id},
    )
    # Skip processing if no blob provided
    if not data_dictionary_blob:
        logging.info("No data dictionary blob provided, skipping processing")
    else:
        try:
            local_DD_path = download_blob_to_tmp(
                container_name="data-dictionaries", blob_name=data_dictionary_blob
            )

            # Read and process the CSV file
            logging.info(f"Reading file from {local_DD_path}")
            with open(local_DD_path, "r", encoding="utf-8") as f:
                csv_content = f.read()

            # Process data dictionary (rows with values)
            data_dictionary_intermediate = [
                row
                for row in csv.DictReader(StringIO(csv_content))
                if row["value"] != ""
            ]
            # Remove BOM from start of file if it's supplied
            dictionary_data = remove_BOM(data_dictionary_intermediate)

            # Convert to nested dictionaries with structure {tables: {fields: {values: value description}}}
            data_dictionary = process_four_item_dict(dictionary_data)
            # Create a temporary table to store the data dictionary
            update_temp_data_dictionary_table(data_dictionary, scan_report_id)
            # Remove the temp file after everything is done
            # TODO: double check with KubernetesExecutor if this is the best way to do this
            os.remove(local_DD_path)
        except Exception as e:
            logging.error(f"Error processing data dictionary: {str(e)}")
            update_job_status(
                stage=JobStageType.UPLOAD_SCAN_REPORT,
                status=StageStatusType.FAILED,
                scan_report=scan_report_id,
                details=f"Upload failed: {str(e)}",
            )
            raise e


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
                INSERT INTO mapping_scanreporttable (scan_report_id, name, created_at, updated_at, trigger_reuse)
                VALUES (%(scan_report_id)s, %(table_name)s, NOW(), NOW(), TRUE)
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
                details=f"Upload failed: {str(e)}",
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
                details=f"Upload failed: {str(e)}",
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
                details=f"Upload failed: {str(e)}",
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
            details="Scan report processing failed: No tables found in the scan report",
        )
    # Remove the temp file after processing
    # TODO: double check with KubernetesExecutor if this is the best way to do this
    os.remove(local_SR_path)
    update_job_status(
        stage=JobStageType.UPLOAD_SCAN_REPORT,
        status=StageStatusType.COMPLETE,
        scan_report=scan_report_id,
    )

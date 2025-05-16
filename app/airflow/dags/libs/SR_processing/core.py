from pathlib import Path
import logging
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.workbook.workbook import Workbook
from libs.utils import pull_validated_params
import os
from libs.enums import StorageType
import csv
from io import StringIO
from libs.SR_processing.utils import (
    remove_BOM,
    process_four_item_dict,
    get_storage_hook,
    get_unique_table_names,
    create_field_entry,
    handle_single_table,
    transform_scan_report_sheet_table,
)
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models.taskinstance import TaskInstance
from typing import List, Tuple, Dict, Any

# Storage type
storage_type = os.getenv("STORAGE_TYPE", StorageType.MINIO)
# Storage hook
storage_hook = get_storage_hook()
# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def get_scan_report(**kwargs) -> None:
    """
    Wrapper function for the scan report processing task using openpyxl

    Args:
        context: Airflow context containing task information

    Returns:
        Dict containing processing results and metadata
    """

    container_name = "scan-reports"
    validated_params = pull_validated_params(kwargs, "validate_params_SR_processing")
    scan_report_blob = validated_params["scan_report_blob"]
    scan_report_id = validated_params["scan_report_id"]
    data_dictionary = kwargs.get("dag_run", {}).conf.get("data_dictionary")
    print(f"data_dictionary: {data_dictionary}")
    local_SR_path = Path(f"/tmp/{scan_report_blob}")

    try:
        # Download file based on storage type
        logging.info(f"Downloading file from {container_name}/{scan_report_blob}")

        if storage_type == StorageType.AZURE:
            storage_hook.get_file(
                file_path=local_SR_path,
                container_name=container_name,
                blob_name=scan_report_blob,
            )
        elif storage_type == StorageType.MINIO:
            s3_object = storage_hook.get_key(
                key=scan_report_blob, bucket_name=container_name
            )
            with open(local_SR_path, "wb") as f:
                s3_object.download_fileobj(f)

    except Exception as e:
        logging.error(f"Error processing scan report: {str(e)}")
        raise


def get_data_dictionary(**kwargs):
    """
    Wrapper function for the data dictionary processing task using openpyxl

    Args:
        context: Airflow context containing task information

    Returns:
        Dict containing processing results and metadata
    """

    validated_params = pull_validated_params(kwargs, "validate_params_SR_processing")
    data_dictionary_blob = validated_params["data_dictionary_blob"]
    # Return empty dictionary if no blob provided
    if not data_dictionary_blob:
        logging.info("No data dictionary blob provided, skipping processing")
        return {}

    container_name = "data-dictionaries"
    local_DD_path = Path(f"/tmp/{data_dictionary_blob}")

    try:
        # Download file based on storage type
        logging.info(f"Downloading file from {container_name}/{data_dictionary_blob}")
        if storage_type == StorageType.AZURE:
            storage_hook.get_file(
                file_path=local_DD_path,
                container_name=container_name,
                blob_name=data_dictionary_blob,
            )
        elif storage_type == StorageType.MINIO:
            s3_object = storage_hook.get_key(
                key=data_dictionary_blob, bucket_name=container_name
            )
            with open(local_DD_path, "wb") as f:
                s3_object.download_fileobj(f)

        # Read the CSV file
        with open(local_DD_path, "r", encoding="utf-8") as f:
            csv_content = f.read()
        # Process data dictionary (rows with values)
        if not csv_content:
            return {}
        else:
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

            return data_dictionary

    except Exception as e:
        logging.error(f"Error processing data dictionary: {str(e)}")
        raise e


def create_scan_report_tables(**kwargs) -> None:
    """
    Creates the scan report tables in the database and returns their IDs.

    Returns:
        Dict containing table names, ids, and name-id pairs
    """

    validated_params = pull_validated_params(kwargs, "validate_params_SR_processing")
    scan_report_id = validated_params["scan_report_id"]
    scan_report_blob = validated_params["scan_report_blob"]
    # Read and process the Excel file
    local_SR_path = Path(f"/tmp/{scan_report_blob}")
    logging.info(f"Reading file from {local_SR_path}")
    workbook = load_workbook(
        filename=local_SR_path, data_only=True, keep_links=False, read_only=True
    )

    worksheet = workbook.worksheets[0]
    table_names = get_unique_table_names(worksheet)

    # Filter out tables that already exist
    new_tables = [name for name in table_names]
    table_pairs: List[Tuple[str, int]] = []

    if new_tables:
        try:
            # Prepare and execute each insert with RETURNING id
            insert_sql = """
                INSERT INTO mapping_scanreporttable (scan_report_id, name, created_at, updated_at)
                VALUES (%(scan_report_id)s, %(table_name)s, NOW(), NOW())
                RETURNING id
            """

            for table_name in new_tables:
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

                field_values_dict = transform_scan_report_sheet_table(
                    workbook[table_name]
                )

                # Create temp table to store field value frequencies
                pg_hook.run(
                    """
                    CREATE TEMP TABLE IF NOT EXISTS temp_field_values (
                        table_id INTEGER,
                        field_name VARCHAR(255),
                        description TEXT,
                        value TEXT,
                        frequency INTEGER
                    )
                """
                )

                # Insert field values data into temp table
                field_values_data = []
                for field_name, values in field_values_dict.items():
                    for value, frequency in values:
                        field_values_data.append(
                            {
                                "table_id": table_id,
                                "field_name": field_name,
                                "value": value,
                                "frequency": frequency,
                            }
                        )

                if field_values_data:
                    pg_hook.insert_rows(
                        table="temp_field_values",
                        rows=[
                            (d["table_id"], d["field_name"], d["value"], d["frequency"])
                            for d in field_values_data
                        ],
                        target_fields=["table_id", "field_name", "value", "frequency"],
                    )

            logging.info(
                f"Added {len(new_tables)} tables to scan report {scan_report_id}."
            )

        except Exception as e:
            logging.error(
                f"Error inserting tables into mapping_scanreporttable: {str(e)}"
            )
            raise e

        try:
            fields_by_table = create_field_entry(worksheet, table_pairs)
            logging.info(f"Created fields grouped by table: {fields_by_table}")

        except Exception as e:
            logging.error(f"Error creating fields grouped by table: {str(e)}")
            raise e

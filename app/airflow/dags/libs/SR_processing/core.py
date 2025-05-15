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


def create_scan_report_tables(**kwargs) -> List[Tuple[str, int]]:
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

            logging.info(
                f"Added {len(new_tables)} tables to scan report {scan_report_id}."
            )

        except Exception as e:
            logging.error(
                f"Error inserting tables into mapping_scanreporttable: {str(e)}"
            )
            raise e

    return table_pairs


def create_fields(**kwargs) -> Dict[str, List[Tuple[str, int]]]:
    """
    Creates fields extracted from the Field Overview worksheet and groups them by table name.

    Returns:
        Dict mapping table names to lists of (field_name, field_id) pairs
    """
    task_instance = kwargs["ti"]
    tables: List[Tuple[str, int]] = task_instance.xcom_pull(
        task_ids="create_scan_report_tables"
    )
    # Read and process the Excel file
    validated_params = pull_validated_params(kwargs, "validate_params_SR_processing")
    scan_report_blob = validated_params["scan_report_blob"]
    local_SR_path = Path(f"/tmp/{scan_report_blob}")
    logging.info(f"Reading file from {local_SR_path}")
    workbook = load_workbook(
        filename=local_SR_path, data_only=True, keep_links=False, read_only=True
    )

    worksheet = workbook.worksheets[0]

    # Initialize dictionary to group fields by table name
    fields_by_table: Dict[str, List[Tuple[str, int]]] = {}

    previous_row_value = None
    for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row + 2):
        # Guard against unnecessary rows beyond the last true row with contents
        if (previous_row_value is None or previous_row_value == "") and (
            row[0].value is None or row[0].value == ""
        ):
            break
        previous_row_value = row[0].value

        # If the row is not empty, then it is a field in a table
        if row[0].value != "" and row[0].value is not None:
            current_table_name = row[0].value
            table = next(t for t in tables if t[0] == current_table_name)

            # Prepare the SQL insert statement with RETURNING id to get the created field ID
            insert_sql = """
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
                RETURNING id
            """

            # Extract values from the row, handling possible None values
            field_name = str(row[1].value) if row[1].value is not None else ""
            description = str(row[2].value) if row[2].value is not None else ""
            type_column = str(row[3].value) if row[3].value is not None else ""
            max_length = row[4].value
            nrows = row[5].value
            nrows_checked = row[6].value

            # Calculate fractions with default values
            fraction_empty = round(float(row[7].value or 0), 2)
            nunique_values = row[8].value
            fraction_unique = round(float(row[9].value or 0), 2)

            # Execute the query and get the returned ID
            result = pg_hook.get_records(
                insert_sql,
                parameters={
                    "scan_report_table_id": table[1],
                    "name": field_name,
                    "description_column": description,
                    "type_column": type_column,
                    "max_length": max_length,
                    "nrows": nrows,
                    "nrows_checked": nrows_checked,
                    "fraction_empty": fraction_empty,
                    "nunique_values": nunique_values,
                    "fraction_unique": fraction_unique,
                },
            )

            # Extract the ID from the result
            field_id = result[0][0]

            # Remove BOM from field name if present
            clean_field_name = field_name.replace("\ufeff", "")

            # Initialize the list for this table if it's the first field
            if str(current_table_name) not in fields_by_table:
                fields_by_table[str(current_table_name)] = []

            # Add the field to the appropriate table group
            fields_by_table[str(current_table_name)].append(
                (clean_field_name, field_id)
            )

            logging.info(
                f"Created field '{clean_field_name}' with ID {field_id} for table '{current_table_name}'"
            )

    logging.info(f"Created fields grouped by table: {fields_by_table}")
    return fields_by_table


def create_values(**kwargs):
    """
    Creates fields extracted from the Field Overview worksheet.

    Loop over all rows in Field Overview sheet.
    This is the same as looping over all fields in all tables.
    When the end of one table is reached, then post all the ScanReportFields
    and ScanReportValues associated to that table, then continue down the
    list of fields in tables.

    Args:
        worksheet (Worksheet): The worksheet containing table names.
        id (str): Scan Report ID to POST to
    """

    task_instance = kwargs["ti"]
    tables: List[Tuple[str, int]] = task_instance.xcom_pull(
        task_ids="create_scan_report_tables"
    )
    fields = task_instance.xcom_pull(task_ids="create_fields")
    data_dictionary = task_instance.xcom_pull(task_ids="get_data_dictionary")
    validated_params = pull_validated_params(kwargs, "validate_params_SR_processing")
    scan_report_blob = validated_params["scan_report_blob"]
    local_SR_path = Path(f"/tmp/{scan_report_blob}")
    workbook = load_workbook(
        filename=local_SR_path, data_only=True, keep_links=False, read_only=True
    )

    for table in tables:
        handle_single_table(table[0], fields[table[0]], workbook, data_dictionary)

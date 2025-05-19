import logging
from openpyxl import load_workbook
from libs.utils import pull_validated_params
import csv
from io import StringIO
from libs.SR_processing.utils import (
    remove_BOM,
    process_four_item_dict,
    get_unique_table_names,
    create_field_entry,
    transform_scan_report_sheet_table,
    create_data_dictionary_table,
    create_field_values_table,
    get_scan_report,
    get_data_dictionary,
)
from airflow.providers.postgres.hooks.postgres import PostgresHook
from typing import List, Tuple
from libs.queries import create_values_query

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def process_data_dictionary(**kwargs) -> None:
    """
    Wrapper function for the data dictionary processing task using openpyxl

    Args:
        context: Airflow context containing task information

    Returns:
        Dict containing processing results and metadata
    """

    validated_params = pull_validated_params(kwargs, "validate_params_SR_processing")
    scan_report_id = validated_params["scan_report_id"]
    data_dictionary_blob = validated_params["data_dictionary_blob"]
    # Return empty dictionary if no blob provided
    if not data_dictionary_blob:
        logging.info("No data dictionary blob provided, skipping processing")
    else:
        local_DD_path = get_data_dictionary(data_dictionary_blob)

        # Read the CSV file
        with open(local_DD_path, "r", encoding="utf-8") as f:
            csv_content = f.read()

        # Process data dictionary (rows with values)
        data_dictionary_intermediate = [
            row for row in csv.DictReader(StringIO(csv_content)) if row["value"] != ""
        ]
        # Remove BOM from start of file if it's supplied
        dictionary_data = remove_BOM(data_dictionary_intermediate)

        # Convert to nested dictionaries with structure {tables: {fields: {values: value description}}}
        data_dictionary = process_four_item_dict(dictionary_data)
        create_data_dictionary_table(data_dictionary, scan_report_id)


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
    local_SR_path = get_scan_report(scan_report_blob)
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
            # Prepare and execute each insert with RETURNING id to build table name and id pairs
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

                create_field_values_table(field_values_dict, table_id, table_name)

        except Exception as e:
            logging.error(
                f"Error inserting tables into mapping_scanreporttable: {str(e)}"
            )
            raise e

        try:
            create_field_entry(worksheet, table_pairs)
            logging.info("Created fields grouped by table")

        except Exception as e:
            logging.error(f"Error creating fields grouped by table: {str(e)}")
            raise e

        try:
            for table_name, table_id in table_pairs:
                # Insert scan report values using data from temporary tables
                pg_hook.run(
                    create_values_query,
                    parameters={
                        "table_id": table_id,
                        "scan_report_id": scan_report_id,
                    },
                )
        except Exception as e:
            logging.error(f"Error creating scan report values: {str(e)}")
            raise e

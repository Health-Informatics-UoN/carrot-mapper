from typing import TypedDict, List, Optional, Any, Dict, Tuple
from airflow.providers.microsoft.azure.hooks.wasb import WasbHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.models.connection import Connection
from airflow.utils.session import create_session
from libs.enums import StorageType
import os
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.workbook.workbook import Workbook
import logging
from collections import defaultdict
from airflow.providers.postgres.hooks.postgres import PostgresHook

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def get_unique_table_names(worksheet: Worksheet) -> List[str]:
    """
    Extracts unique table names from the Field Overview worksheet.

    Args:
        worksheet: The worksheet containing table names.

    Returns:
        List[str]: A list of unique table names.
    """
    # Get all the table names in the order they appear in the Field Overview page
    table_names = []
    # Iterate over cells in the first column, but because we're in ReadOnly mode we
    # can't do that in the simplest manner.
    worksheet.calculate_dimension()
    for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
        cell_value = row[0].value
        if cell_value and isinstance(cell_value, str) and cell_value not in table_names:
            # Truncate table names because sheet names are truncated to 31 characters in Excel
            # NOTE: This can casue the table names to be duplicated
            table_names.append(cell_value[:31])
    return table_names


storage_type = os.getenv("STORAGE_TYPE", StorageType.MINIO)


def connect_to_storage():
    with create_session() as session:
        if storage_type == StorageType.AZURE:
            # Check if WASB connection exists
            existing_conn = (
                session.query(Connection)
                .filter(Connection.conn_id == "wasb_conn")
                .first()
            )

            if existing_conn is None:
                conn = Connection(
                    conn_id="wasb_conn",
                    conn_type="wasb",
                    extra={
                        "connection_string": os.getenv(
                            "AIRFLOW_VAR_WASB_CONNECTION_STRING"
                        ),
                    },
                )
                session.add(conn)
                session.commit()
                logging.info("Created new WASB connection")

        elif storage_type == StorageType.MINIO:
            # Check if MinIO connection exists
            existing_conn = (
                session.query(Connection)
                .filter(Connection.conn_id == "minio_conn")
                .first()
            )

            if existing_conn is None:
                conn = Connection(
                    conn_id="minio_conn",
                    conn_type="aws",
                    extra={
                        "endpoint_url": os.getenv("AIRFLOW_VAR_MINIO_ENDPOINT"),
                        "aws_access_key_id": os.getenv("AIRFLOW_VAR_MINIO_ACCESS_KEY"),
                        "aws_secret_access_key": os.getenv(
                            "AIRFLOW_VAR_MINIO_SECRET_KEY"
                        ),
                    },
                )
                session.add(conn)
                session.commit()
                logging.info("Created new MinIO connection")


def get_storage_hook():
    if storage_type == StorageType.AZURE:
        return WasbHook(wasb_conn_id="wasb_conn")
    elif storage_type == StorageType.MINIO:
        return S3Hook(aws_conn_id="minio_conn")
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


def remove_BOM(intermediate: List[Dict[str, Any]]):
    """
    Given a list of dictionaries, remove any occurrences of the BOM in the keys.

    Args:
        intermediate (List[Dict[str, Any]]): List of dictionaries to remove from.

    Returns:
        The list of dictionaries with BOM removed from the keys.
    """
    return [
        {key.replace("\ufeff", ""): value for key, value in d.items()}
        for d in intermediate
    ]


def process_four_item_dict(four_item_data):
    """
    Converts a list of dictionaries (each with keys 'csv_file_name', 'field_name' and
    'code' and 'value') to a nested dictionary with indices 'csv_file_name',
    'field_name', 'code', and internal value 'value'.

    [{'csv_file_name': 'table1', 'field_name': 'field1', 'value': 'value1', 'code':
    'code1'},
    {'csv_file_name': 'table1', 'field_name': 'field2', 'value': 'value2', 'code':
    'code2'},
    {'csv_file_name': 'table2', 'field_name': 'field2', 'value': 'value2', 'code':
    'code2'},
    {'csv_file_name': 'table2', 'field_name': 'field2', 'value': 'value3', 'code':
    'code3'},
    {'csv_file_name': 'table3', 'field_name': 'field3', 'value': 'value3', 'code':
    'code3'}]
    ->
    {'table1': {'field1': {'value1': 'code1'}, 'field2': {'value2': 'code2'}},
    'table2': {'field2': {'value2': 'code2', 'value3': 'code3'}},
    'table3': {'field3': {'value3': 'code3'}}
    }
    """
    csv_file_names = set(row["csv_file_name"] for row in four_item_data)

    # Initialise the dictionary with the keys, and each value set to a blank dict()
    new_data_dictionary = dict.fromkeys(csv_file_names, {})

    for row in four_item_data:
        if row["field_name"] not in new_data_dictionary[row["csv_file_name"]]:
            new_data_dictionary[row["csv_file_name"]][row["field_name"]] = {}
        new_data_dictionary[row["csv_file_name"]][row["field_name"]][row["code"]] = row[
            "value"
        ]

    return new_data_dictionary


def transform_scan_report_sheet_table(sheet: Worksheet) -> defaultdict[Any, List]:
    """
    Transforms a worksheet data into a JSON like format.

    Args:
        sheet (Worksheet): Sheet of data to transform

    Returns:
        defaultdict[Any, List]: The transformed data.
    """
    logging.debug("Start process_scan_report_sheet_table")

    sheet.calculate_dimension()
    # Get header entries (skipping every second column which is just 'Frequency')
    # So sheet_headers = ['a', 'b']
    first_row = sheet[1]
    sheet_headers = [cell.value for cell in first_row[::2]]

    # Set up an empty defaultdict, and fill it with one entry per header (i.e. one
    # per column)
    # Append each entry's value with the tuple (value, frequency) so that we end up
    # with each entry containing one tuple per non-empty entry in the column.
    #
    # This will give us
    #
    # ordereddict({'a': [('apple', 20), ('banana', 3), ('pear', 12)],
    #              'b': [('orange', 5), ('plantain', 50)]})

    d = defaultdict(list)
    # Iterate over all rows beyond the header - use the number of sheet_headers*2 to
    # set the maximum column rather than relying on sheet.max_col as this is not
    # always reliably updated by Excel etc.
    for row in sheet.iter_rows(
        min_col=1,
        max_col=len(sheet_headers) * 2,
        min_row=2,
        max_row=sheet.max_row,
        values_only=True,
    ):
        # Set boolean to track whether we hit a blank row for early exit below.
        this_row_empty = True
        # Iterate across the pairs of cells in the row. If the pair is non-empty,
        # then add it to the relevant dict entry.
        for header, cell, freq in zip(sheet_headers, row[::2], row[1::2]):
            if (cell != "" and cell is not None) or (freq != "" and freq is not None):
                d[header].append((str(cell), freq))
                this_row_empty = False
        # This will trigger if we hit a row that is entirely empty. Short-circuit
        # to exit early here - this saves us from situations where sheet.max_row is
        # incorrectly set (too large)
        if this_row_empty:
            break
    # Clean BOM characters from keys before returning
    cleaned_dict = defaultdict(list)
    for key, value in d.items():
        clean_key = key.replace("\ufeff", "") if isinstance(key, str) else key
        cleaned_dict[clean_key] = value

    logging.debug("Finish process_scan_report_sheet_table")
    return cleaned_dict


def _create_values_details(
    fieldname_value_freq: Dict[str, Tuple[str]],
    table_name: str,
) -> List[Dict[str, Any]]:
    """
    Create value details for each fieldname-value pair.

    Args:
        fieldname_value_freq (Dict[str, Tuple[str]]): A dictionary mapping fieldnames to
            tuples of value-frequency pairs.
        table_name (str): The name of the table.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing the value details for each
            fieldname-value pair.
    """
    values_details = []
    for fieldname, value_freq_tuples in fieldname_value_freq.items():
        for full_value, frequency in value_freq_tuples:
            try:
                frequency = int(frequency)
            except (ValueError, TypeError):
                frequency = 0
            values_details.append(
                {
                    "full_value": full_value,
                    "frequency": frequency,
                    "fieldname": fieldname,
                    "table": table_name,
                    "val_desc": None,
                }
            )
    return values_details


def _assign_order(values_details: List[Dict[str, Any]]) -> None:
    """
    Add "order" field to each entry to enable correctly-ordered recombination at the end.

    Args:
        values_details (List[Dict[str, Any]]): List of value details to transform.

    Returns:
        None
    """
    for entry_number, entry in enumerate(values_details):
        entry["order"] = entry_number


def _apply_data_dictionary(
    values_details: List[Dict[str, Any]], data_dictionary: Dict[Any, Dict]
) -> None:
    """
    Apply data dictionary to update value descriptions in values_details from the data dict.

    Args:
        values_details (List[Dict[str, Any]]): A list of dictionaries with the value
            details for each fieldname-value pair.
        data_dictionary (Dict[Any, Dict]): A dictionary mapping table names to dictionaries
            containing fieldname-value mappings and their corresponding value descriptions.

    Returns:
        None
    """
    for entry in values_details:
        table_data = data_dictionary.get(str(entry["table"]))
        if table_data and table_data.get(str(entry["fieldname"])):
            entry["val_desc"] = table_data[str(entry["fieldname"])].get(
                str(entry["full_value"])
            )


def _create_value_entries(
    values_details: List[Dict[str, Any]], fields: List[Tuple[str, int]]
):
    """
    Create value entries based on values_details and fieldnames_to_ids_dict.

    Args:
        values_details (List[Dict[str, Any]]): A list of dictionaries of the value
            details for each fieldname-value pair.
        fields (List[ScanReportField]): A list of SCan Report Fields.

    Returns:
        List[ScanReportValue]: A list of ScanReportValues.
    """
    print(f"values_details: {values_details}")
    print(f"fields: {fields}")
    try:
        for field in fields:
            scan_report_field_id = field[1]
            for entry in values_details:
                if entry["fieldname"] == field[0]:
                    value = entry["full_value"]
                    frequency = entry["frequency"]
                    value_description = entry["val_desc"]
                    # Prepare the SQL insert statement with RETURNING id to get the created field ID
                    insert_sql = """
                    INSERT INTO mapping_scanreportvalue (
                        scan_report_field_id, value, frequency, value_description, "conceptID", created_at, updated_at
                    )
                    VALUES (
                        %(scan_report_field_id)s, %(value)s, %(frequency)s, %(value_description)s, -1, NOW(), NOW()
                    )
                """
                    # Execute the query and get the returned ID
                    pg_hook.run(
                        insert_sql,
                        parameters={
                            "scan_report_field_id": scan_report_field_id,
                            "value": value,
                            "frequency": frequency,
                            "value_description": value_description,
                        },
                    )

    except Exception as e:
        logging.error(f"Error creating field entry: {str(e)}")
        raise e


def add_SRValues_and_value_descriptions(
    fieldname_value_freq_dict: Dict[str, Tuple[str]],
    current_table_name: str,
    data_dictionary: Dict[Any, Dict],
    fields: List[Tuple[str, int]],
) -> None:
    """
    Add ScanReportValues and value descriptions to the values_details list.

    Args:
        fieldname_value_freq_dict: A dictionary containing field names as keys and
            value-frequency tuples as values.
        current_table_name: The name of the current table.
        data_dictionary: The data dictionary containing field-value descriptions.
        fields: A list of Scan Report Fields.

    Returns:
        The response content after posting the values.
    """
    values_details = _create_values_details(
        fieldname_value_freq_dict, current_table_name
    )
    logging.debug("Assign order")
    _assign_order(values_details)

    # --------------------------------------------------------------------------------
    # Update val_desc of each SRField entry if it has a value description from the
    # data dictionary
    if data_dictionary:
        logging.debug("apply data dictionary")
        _apply_data_dictionary(values_details, data_dictionary)

    # Convert basic information about SRValues into entries
    logging.debug("create value_entries_to_post")
    _create_value_entries(values_details, fields)


def create_field_entry(
    worksheet: Worksheet, tables: List[Tuple[str, int]]
) -> Dict[str, List[Tuple[str, int]]]:
    """
    Creates a field entry in the database for a scan report table.

    Args:
        row: The worksheet row containing field data
        scan_report_table_id: The ID of the scan report table

    Returns:
        The ID of the newly created field
    """
    try:
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

        return fields_by_table

    except Exception as e:
        logging.error(f"Error creating field entry: {str(e)}")
        raise e


def handle_single_table(
    current_table_name: str,
    fields: list[Tuple[str, int]],
    workbook: Workbook,
    data_dictionary: Dict[Any, Dict],
) -> None:
    """
    Handle creating a single table values.

    Args:
        field_entries (List[Dict[str, str]]): List of field entries to create.
        scan_report_id (str): ID of the scan report to attach to.

    Raises:
        Exception: ValueError: Trying to access a sheet in the workbook that does not exist.
    """

    # Go to Table sheet to process all the values from the sheet
    sheet = workbook[current_table_name]

    fieldname_value_freq_dict = transform_scan_report_sheet_table(sheet)
    add_SRValues_and_value_descriptions(
        fieldname_value_freq_dict,
        current_table_name,
        data_dictionary,
        fields,
    )

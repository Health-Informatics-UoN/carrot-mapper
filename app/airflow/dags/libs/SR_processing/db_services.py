from typing import List, Any, Dict, Tuple
from openpyxl.worksheet.worksheet import Worksheet
from libs.queries import create_fields_query
import logging
from collections import defaultdict
from airflow.providers.postgres.hooks.postgres import PostgresHook
from libs.SR_processing.helpers import default_zero

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def create_field_entries(
    worksheet: Worksheet, table_pairs: List[Tuple[str, int]]
) -> None:
    """
    Creates field entries in the database for a scan report table.

    Args:
        row: The worksheet row containing field data
        scan_report_table_id: The ID of the scan report table

    Returns:
        The ID of the newly created field
    """
    try:
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
                # table_pair[0] is table name, table_pair[1] is table id
                table = next(
                    table_pair
                    for table_pair in table_pairs
                    if table_pair[0] == current_table_name
                )

                # Extract values from the row, handling possible None values
                field_name = str(row[1].value) if row[1].value is not None else ""
                description = str(row[2].value) if row[2].value is not None else ""
                type_column = str(row[3].value) if row[3].value is not None else ""
                max_length = row[4].value
                nrows = row[5].value
                nrows_checked = row[6].value

                # Calculate fractions with default values
                fraction_empty = round(default_zero(row[7].value), 2)
                nunique_values = row[8].value
                fraction_unique = round(default_zero(row[9].value), 2)

                # Execute the query and get the returned ID
                pg_hook.run(
                    create_fields_query,
                    parameters={
                        # table[1] is table id
                        "scan_report_table_id": table[1],
                        "name": field_name.replace("\ufeff", ""),
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

    except Exception as e:
        logging.error(f"Error creating field entry: {str(e)}")
        raise e


def create_temp_data_dictionary_table(
    data_dictionary: Dict[str, Dict[str, Dict[str, str]]], scan_report_id: int
) -> None:
    """
    Creates a temporary table to store data dictionary information.

    Args:
        data_dictionary: A dictionary of data dictionary information
        scan_report_id: The ID of the scan report

    Returns:
        None
    """

    if not data_dictionary:
        logging.info("No data dictionary available, skipping dictionary table creation")
        return

    try:
        # Create temporary table for data dictionary
        pg_hook.run(
            """
            DROP TABLE IF EXISTS temp_data_dictionary_%(scan_report_id)s;
            CREATE TABLE temp_data_dictionary_%(scan_report_id)s (
                table_name VARCHAR(255),
                field_name VARCHAR(255),
                value TEXT,
                value_description TEXT
            )
        """,
            parameters={"scan_report_id": scan_report_id},
        )

        # Prepare data for insertion
        dictionary_records = []
        for table_name, fields in data_dictionary.items():
            for field_name, values in fields.items():
                for value, description in values.items():
                    dictionary_records.append(
                        {
                            "table_name": table_name,
                            "field_name": field_name,
                            "value": value,
                            "value_description": description,
                        }
                    )

        # Insert records into the temporary table
        if dictionary_records:
            pg_hook.insert_rows(
                table=f"temp_data_dictionary_{scan_report_id}",
                rows=[
                    (
                        d["table_name"],
                        d["field_name"],
                        d["value"],
                        d["value_description"],
                    )
                    for d in dictionary_records
                ],
                target_fields=[
                    "table_name",
                    "field_name",
                    "value",
                    "value_description",
                ],
            )

        logging.info(
            f"Created temporary data dictionary table with {len(dictionary_records)} records"
        )

    except Exception as e:
        logging.error(f"Error creating data dictionary table: {str(e)}")
        raise e


def create_temp_field_values_table(
    field_values_dict: defaultdict[Any, List], table_id: int
) -> None:
    """
    Creates a temporary table to store field values and their frequencies.

    Args:
        field_values_dict: A dictionary of field values and their frequencies
        table_id: The ID of the table

    Returns:
        None
    """

    if not field_values_dict:
        logging.info("No field-values available, skipping field values table creation")
        return

    try:
        # Create temp table to store field value frequencies
        pg_hook.run(
            """
            DROP TABLE IF EXISTS temp_field_values_%(table_id)s;
            CREATE TABLE IF NOT EXISTS temp_field_values_%(table_id)s (
                field_name VARCHAR(255),
                value TEXT,
                frequency INTEGER
            )
        """,
            parameters={"table_id": table_id},
        )

        # Insert field values data into temp table
        field_values_data = []
        for field_name, values in field_values_dict.items():
            for value, frequency in values:
                # TODO: confirm about frequency of "List truncated..."
                # Convert empty strings or None to 0 for frequency
                if frequency == "" or frequency is None:
                    frequency = 0

                # Ensure frequency is an integer
                try:
                    frequency = int(frequency)
                except (ValueError, TypeError):
                    frequency = 0

                field_values_data.append(
                    {
                        "field_name": field_name,
                        "value": value,
                        "frequency": frequency,
                    }
                )

        if field_values_data:
            pg_hook.insert_rows(
                table=f"temp_field_values_{table_id}",
                rows=[
                    (
                        d["field_name"],
                        d["value"],
                        d["frequency"],
                    )
                    for d in field_values_data
                ],
                target_fields=[
                    "field_name",
                    "value",
                    "frequency",
                ],
            )

    except Exception as e:
        logging.error(f"Error creating data dictionary table: {str(e)}")
        raise e

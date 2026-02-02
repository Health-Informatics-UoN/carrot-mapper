import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from airflow.providers.postgres.hooks.postgres import PostgresHook
from libs.enums import JobStageType, StageStatusType
from libs.queries import create_fields_query
from libs.settings import (
    AIRFLOW_DAGRUN_TIMEOUT,
    AIRFLOW_DEBUG_MODE,
    EXECUTE_VALUES_PAGE_SIZE,
    TEMP_TABLE_CLEANUP_DELAY,
)
from libs.utils import update_job_status
from openpyxl.worksheet.worksheet import Worksheet
from psycopg2.extras import execute_values

# PostgreSQL connection hook
pg_hook = PostgresHook(
    postgres_conn_id="postgres_db_conn",
    options=f"-c statement_timeout={float(AIRFLOW_DAGRUN_TIMEOUT) * 60 * 1000}ms",
)


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

                pg_hook.run(
                    create_fields_query,
                    parameters={
                        # table[1] is table id
                        "scan_report_table_id": table[1],
                        "name": field_name,  # NOTE: without BOM removal to keep the consistency with Azure functions
                        "description_column": description,
                        "type_column": type_column,
                    },
                )

    except Exception as e:
        logging.error(f"Error creating field entry: {str(e)}")
        raise e


def update_temp_data_dictionary_table(
    data_dictionary: Dict[str, Dict[str, Dict[str, str]]], scan_report_id: int
) -> None:
    """
    Updates the temporary table to store data dictionary information.

    Args:
        data_dictionary: A dictionary of data dictionary information
        scan_report_id: The ID of the scan report

    Returns:
        None
    """
    # Skip updating the temporary table if no data dictionary provided
    if not data_dictionary:
        logging.info(
            "No data dictionary (4 items list) available, skipping dictionary table creation"
        )
        return

    try:
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
            # Get a database connection - this automatically commits on success or rolls back on error
            with pg_hook.get_conn() as conn:
                # Create a cursor for executing SQL - this automatically closes when we're done
                with conn.cursor() as cursor:
                    # Bulk insert all records efficiently using execute_values
                    execute_values(
                        cursor,
                        f"INSERT INTO temp_data_dictionary_{scan_report_id} (table_name, field_name, value, value_description) VALUES %s",
                        [
                            (
                                d["table_name"],
                                d["field_name"],
                                d["value"],
                                d["value_description"],
                            )
                            for d in dictionary_records
                        ],
                        page_size=EXECUTE_VALUES_PAGE_SIZE,
                    )
                    conn.commit()

        logging.info(
            f"Created temporary data dictionary table with {len(dictionary_records)} records"
        )

    except Exception as e:
        logging.error(f"Error creating data dictionary table: {str(e)}")
        update_job_status(
            stage=JobStageType.UPLOAD_SCAN_REPORT,
            status=StageStatusType.FAILED,
            scan_report=scan_report_id,
            details=f"Upload failed: {str(e)}",
        )
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
            with pg_hook.get_conn() as conn:
                with conn.cursor() as cursor:
                    execute_values(
                        cursor,
                        f"INSERT INTO temp_field_values_{table_id} (field_name, value, frequency) VALUES %s",
                        [
                            (d["field_name"], d["value"], d["frequency"])
                            for d in field_values_data
                        ],
                        page_size=EXECUTE_VALUES_PAGE_SIZE,
                    )
                    conn.commit()

    except Exception as e:
        logging.error(f"Error creating data dictionary table: {str(e)}")
        raise e


def delete_temp_tables(scan_report_id: int, table_pairs: List[Tuple[str, int]]) -> None:
    """
    Deletes the temporary tables for a scan report.

    Args:
        scan_report_id: The ID of the scan report
        table_pairs: A list of tuples containing the table name and ID
    """
    try:
        if AIRFLOW_DEBUG_MODE == "true":
            return
        pg_hook.run(f"DROP TABLE IF EXISTS temp_data_dictionary_{scan_report_id}")
        for _, table_id in table_pairs:
            pg_hook.run(f"DROP TABLE IF EXISTS temp_field_values_{table_id}")
    except Exception as e:
        logging.error(f"Error deleting temporary tables: {str(e)}")
        raise e


def cleanup_temp_tables_for_scan_report(scan_report_id: int) -> List[Tuple[str, int]]:
    """
    Clean up temporary tables for a scan report.

    Deletes temporary tables (temp_data_dictionary and temp_field_values) for all tables
    associated with the given scan_report_id in mapping_scanreporttable.

    Returns:
        List of (table_name, table_id) tuples for the tables that were cleaned up.
    """

    query = """
        SELECT name, id
        FROM mapping_scanreporttable
        WHERE scan_report_id = %(scan_report_id)s
    """
    records = pg_hook.get_records(query, parameters={"scan_report_id": scan_report_id})
    table_pairs = [(record[0], record[1]) for record in records] if records else []
    if table_pairs:
        delete_temp_tables(scan_report_id, table_pairs)
    return table_pairs

def handle_failure_and_cleanup_temp_tables(context):
    """
    Delete temporary tables when the DAG fails or times out.

    This handles cleanup when failures happen outside the normal pipeline code, like
    timeouts or external errors. Since the tables are already in the database even if
    the DAG fails, we query mapping_scanreporttable to find all tables for this
    scan_report_id, then delete the temp tables (temp_data_dictionary and
    temp_field_values).

    When a timeout occurs, the task that was running may still be creating temporary tables in the background.
    This function waits TEMP_TABLE_CLEANUP_DELAY seconds first so any in-flight table creation can finish,
    then runs a single cleanup pass. Cleanup is not urgent, so waiting once is simpler than cleaning twice.


    Args:
        context: Airflow execution context containing task_instance, dag, dag_run, etc.
    """
    try:
        dag_run = context["dag_run"]
        dag = context.get("dag")
        dag_run_conf = dag_run.conf or {}
        scan_report_id = dag_run_conf.get("scan_report_id")

        if not scan_report_id:
            logging.warning(
                "No scan_report_id found in DAG run configuration, skipping temp table cleanup"
            )
            return

        # Update job status to FAILED for scan_report_processing DAG
        if dag and dag.dag_id == "scan_report_processing":
            try:
                update_job_status(
                    stage=JobStageType.UPLOAD_SCAN_REPORT,
                    status=StageStatusType.FAILED,
                    scan_report=scan_report_id,
                    details="Scan report processing DAG timed out or failed.",
                )
                logging.info(
                    "Updated job status to FAILED for scan_report_id=%s",
                    scan_report_id,
                )
            except Exception as e:
                logging.error("Failed to update job status on failure: %s", str(e))

        # Wait so a timed-out task can finish creating tables, then delete the temporary tables
        delay = TEMP_TABLE_CLEANUP_DELAY
        time.sleep(delay)

        table_pairs = cleanup_temp_tables_for_scan_report(scan_report_id)
        if table_pairs:
            logging.info(
                "Deleted temp tables for scan_report_id=%s (n=%d)",
                scan_report_id,
                len(table_pairs),
            )
        logging.info(
            "Completed temp table cleanup for scan_report_id=%s", scan_report_id
        )

    except Exception as e:
        logging.error("Failed to delete temporary tables on failure: %s", str(e))
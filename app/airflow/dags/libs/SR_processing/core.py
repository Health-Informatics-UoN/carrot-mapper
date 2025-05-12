from airflow.providers.microsoft.azure.hooks.wasb import WasbHook
from pathlib import Path
from typing import Dict, Any
import logging
from openpyxl import load_workbook
from openpyxl.cell.cell import Cell
from openpyxl.worksheet.worksheet import Worksheet
from libs.utils import (
    pull_validated_params,
)
from airflow.models.connection import Connection
from airflow.utils.session import create_session
import os

logger = logging.getLogger(__name__)


def create_wasb_connection():
    with create_session() as session:
        # Check if connection already exists
        existing_conn = (
            session.query(Connection).filter(Connection.conn_id == "wasb_conn").first()
        )

        if existing_conn is None:
            # Only create if connection doesn't exist
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
            logger.info("Created new WASB connection")
        else:
            logger.debug("WASB connection already exists, skipping creation")


create_wasb_connection()
hook = WasbHook(wasb_conn_id="wasb_conn")


def process_scan_report_task(**kwargs):
    """
    Wrapper function for the scan report processing task using openpyxl

    Args:
        context: Airflow context containing task information

    Returns:
        Dict containing processing results and metadata
    """

    container_name = "scan-reports"
    validated_params = pull_validated_params(kwargs, "validate_params")
    scan_report_blob = validated_params["scan_report_blob"]
    local_file_path = Path(f"/tmp/{scan_report_blob}")

    try:
        # Download file
        logger.info(f"Downloading file from {container_name}/{scan_report_blob}")
        hook.get_file(
            file_path=local_file_path,
            container_name=container_name,
            blob_name=scan_report_blob,
        )

        # Read the Excel file using openpyxl
        logger.info(f"Reading file from {local_file_path}")
        workbook = load_workbook(filename=local_file_path, read_only=True)

        # Process the first worksheet (or you can specify the sheet name)
        worksheet = workbook.active
        print(worksheet)
        # Example processing logic using openpyxl
        processed_data = []
        total_rows = 0

        # Get headers from first row
        headers = [cell.value for cell in next(worksheet.rows)]
        print(headers)
        # Process each row
        for row in worksheet.iter_rows(min_row=2):  # Skip header row
            row_data = {}
            for header, cell in zip(headers, row):
                row_data[header] = cell.value
            processed_data.append(row_data)
            total_rows += 1

        # Example: Process specific columns or perform calculations
        # You can add your specific processing logic here

        workbook.close()

    except Exception as e:
        logger.error(f"Error processing scan report: {str(e)}")
        raise
    finally:
        # Clean up
        if "workbook" in locals():
            workbook.close()
        if local_file_path.exists():
            local_file_path.unlink()

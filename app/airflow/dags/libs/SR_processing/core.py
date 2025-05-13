from airflow.providers.microsoft.azure.hooks.wasb import WasbHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
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
storage_type = os.getenv("AIRFLOW_VAR_STORAGE_TYPE", "minio").lower()


def connect_to_storage():

    with create_session() as session:
        if storage_type == "azure":
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
                logger.info("Created new WASB connection")

        elif storage_type == "minio":
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
                logger.info("Created new MinIO connection")


def _get_storage_hook():

    if storage_type == "azure":
        return WasbHook(wasb_conn_id="wasb_conn")
    elif storage_type == "minio":
        return S3Hook(aws_conn_id="minio_conn")
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


def process_scan_report_task(**kwargs):
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
    local_file_path = Path(f"/tmp/{scan_report_blob}")
    hook = _get_storage_hook()

    try:
        # Download file based on storage type
        logger.info(f"Downloading file from {container_name}/{scan_report_blob}")

        if storage_type == "azure":
            hook.get_file(
                file_path=local_file_path,
                container_name=container_name,
                blob_name=scan_report_blob,
            )
        else:  # MinIO/S3
            s3_object = hook.get_key(key=scan_report_blob, bucket_name=container_name)
            with open(local_file_path, "wb") as f:
                s3_object.download_fileobj(f)

        # Read and process the Excel file
        logger.info(f"Reading file from {local_file_path}")
        workbook = load_workbook(filename=local_file_path, read_only=True)
        worksheet = workbook.active

        processed_data = []
        total_rows = 0

        # Get headers from first row
        headers = [cell.value for cell in next(worksheet.rows)]

        # Process each row
        for row in worksheet.iter_rows(min_row=2):  # Skip header row
            row_data = {}
            for header, cell in zip(headers, row):
                row_data[header] = cell.value
            processed_data.append(row_data)
            total_rows += 1

        workbook.close()
        return processed_data

    except Exception as e:
        logger.error(f"Error processing scan report: {str(e)}")
        raise
    finally:
        # Clean up
        if "workbook" in locals():
            workbook.close()
        if local_file_path.exists():
            local_file_path.unlink()

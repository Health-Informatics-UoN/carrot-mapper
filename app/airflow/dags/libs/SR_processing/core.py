from pathlib import Path
from typing import Dict, Any
import logging
from openpyxl import load_workbook
from openpyxl.cell.cell import Cell
from openpyxl.worksheet.worksheet import Worksheet
from libs.utils import (
    pull_validated_params,
)

import os
from libs.enums import StorageType
from libs.utils import get_storage_hook


storage_type = os.getenv("STORAGE_TYPE", StorageType.MINIO)
hook = get_storage_hook()


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

    try:
        # Download file based on storage type
        logging.info(f"Downloading file from {container_name}/{scan_report_blob}")

        if storage_type == StorageType.AZURE:
            hook.get_file(
                file_path=local_file_path,
                container_name=container_name,
                blob_name=scan_report_blob,
            )
        elif storage_type == StorageType.MINIO:
            s3_object = hook.get_key(key=scan_report_blob, bucket_name=container_name)
            with open(local_file_path, "wb") as f:
                s3_object.download_fileobj(f)

        # Read and process the Excel file
        logging.info(f"Reading file from {local_file_path}")
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
        logging.error(f"Error processing scan report: {str(e)}")
        raise
    finally:
        # Clean up
        if "workbook" in locals():
            workbook.close()
        if local_file_path.exists():
            local_file_path.unlink()

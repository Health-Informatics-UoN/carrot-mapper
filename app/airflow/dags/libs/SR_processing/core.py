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


def get_scan_report(**kwargs):
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
    local_SR_path = Path(f"/tmp/scan-reports/{scan_report_blob}")

    try:
        # Download file based on storage type
        logging.info(f"Downloading file from {container_name}/{scan_report_blob}")

        if storage_type == StorageType.AZURE:
            hook.get_file(
                file_path=local_SR_path,
                container_name=container_name,
                blob_name=scan_report_blob,
            )
        elif storage_type == StorageType.MINIO:
            s3_object = hook.get_key(key=scan_report_blob, bucket_name=container_name)
            with open(local_SR_path, "wb") as f:
                s3_object.download_fileobj(f)

        return local_SR_path

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

    container_name = "data-dictionaries"
    validated_params = pull_validated_params(kwargs, "validate_params_SR_processing")
    data_dictionary_blob = validated_params["data_dictionary_blob"]
    local_DD_path = Path(f"/tmp/data-dictionaries/{data_dictionary_blob}")

    try:
        # Download file based on storage type
        logging.info(f"Downloading file from {container_name}/{data_dictionary_blob}")

        if storage_type == StorageType.AZURE:
            hook.get_file(
                file_path=local_DD_path,
                container_name=container_name,
                blob_name=data_dictionary_blob,
            )
        elif storage_type == StorageType.MINIO:
            s3_object = hook.get_key(
                key=data_dictionary_blob, bucket_name=container_name
            )
            with open(local_DD_path, "wb") as f:
                s3_object.download_fileobj(f)

        return local_DD_path

    except Exception as e:
        logging.error(f"Error processing data dictionary: {str(e)}")
        raise

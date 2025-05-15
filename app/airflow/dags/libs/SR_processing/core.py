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
import csv
from io import StringIO
from libs.utils import remove_BOM, process_four_item_dict


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
    data_dictionary = kwargs.get("dag_run", {}).conf.get("data_dictionary")
    print(f"data_dictionary: {data_dictionary}")
    local_SR_path = Path(f"/tmp/{scan_report_blob}")

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

        # Read and process the Excel file
        logging.info(f"Reading file from {local_SR_path}")
        workbook = load_workbook(filename=local_SR_path, read_only=True)
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
    local_DD_path = Path(f"/tmp/{data_dictionary_blob}")

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

        return data_dictionary

    except Exception as e:
        logging.error(f"Error processing data dictionary: {str(e)}")
        raise

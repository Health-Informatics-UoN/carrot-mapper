import logging
from libs.utils import pull_validated_params
from airflow.providers.postgres.hooks.postgres import PostgresHook
from libs.types import FileHandlerConfig
from libs.rules_export.file_services import build_rules_json, build_rules_csv
from typing import Dict
from datetime import datetime
from libs.queries import create_update_temp_rules_table_query, create_file_entry_query
from libs.storage_services import upload_blob_to_storage
from libs.enums import JobStageType, StageStatusType
from libs.utils import update_job_status

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def pre_process_rules(**kwargs) -> None:
    """
    Wrapper function for the rules export processing task using openpyxl

    Args:
        context: Airflow context containing task information

    Returns:
        None
    """
    # Pull validated params
    validated_params = pull_validated_params(kwargs, "validate_params_rules_export")
    scan_report_id = validated_params["scan_report_id"]
    try:
        #  Create or update the temp table with the processed rules data
        pg_hook.run(
            create_update_temp_rules_table_query,
            parameters={"scan_report_id": scan_report_id},
        )
    except Exception as e:
        logging.error(f"Error creating or updating the temp table: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            stage=JobStageType.DOWNLOAD_RULES,
            status=StageStatusType.FAILED,
            details=f"Error creating or updating the temp table for rules export for scan report {scan_report_id}",
        )
        raise e


def build_and_upload_rules_file(**kwargs) -> None:
    """
    Build and upload rules file
    """
    # Pull validated params
    validated_params = pull_validated_params(kwargs, "validate_params_rules_export")
    scan_report_id = validated_params["scan_report_id"]
    user_id = validated_params["user_id"]
    scan_report_name = validated_params["scan_report_name"]
    file_type = validated_params["file_type"]

    # Setup file config. (Credit: @AndyRae)
    file_handlers: Dict[str, FileHandlerConfig] = {
        "text/csv": FileHandlerConfig(
            lambda: build_rules_csv(scan_report_id),
            "mapping_csv",
            "csv",
        ),
        "application/json": FileHandlerConfig(
            lambda: build_rules_json(scan_report_name, scan_report_id),
            "mapping_json",
            "json",
        ),
    }
    config = file_handlers[file_type]

    # Generate it
    file = config.handler()
    file_type_value = config.file_type_value
    file_extension = config.file_extension

    # build file name
    filename = f"Rules - {scan_report_name} - {scan_report_id} - {datetime.now()}.{file_extension}"

    # Upload to blob storage
    upload_blob_to_storage(
        container_name="rules-exports",
        blob_name=filename,
        data=file,
        content_type=file_type,
    )

    # Get file_type_id from files_filetype table
    file_type_id_query = """
        SELECT id FROM files_filetype WHERE value = %(file_type_value)s
    """
    file_type_id_result = pg_hook.get_first(
        file_type_id_query, parameters={"file_type_value": file_type_value}
    )
    if not file_type_id_result:
        raise ValueError(f"No file type found for value: {file_type_value}")
    file_type_id = file_type_id_result[0]

    try:
        # Create file entry in the database
        pg_hook.run(
            create_file_entry_query,
            parameters={
                "name": filename,
                "file_url": filename,
                "user_id": user_id,
                "file_type_id": file_type_id,
                "scan_report_id": scan_report_id,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        )
        update_job_status(
            scan_report=scan_report_id,
            stage=JobStageType.DOWNLOAD_RULES,
            status=StageStatusType.COMPLETE,
            details="Rules file successfully created and uploaded to blob storage",
        )
    except Exception as e:
        logging.error(f"Error creating file entry: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            stage=JobStageType.DOWNLOAD_RULES,
            status=StageStatusType.FAILED,
            details=f"Error creating file entry in the database for scan report {scan_report_id}",
        )
        raise e

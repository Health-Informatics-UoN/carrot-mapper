import logging
from libs.utils import pull_validated_params
from airflow.providers.postgres.hooks.postgres import PostgresHook
from libs.types import FileHandlerConfig
from libs.rules_export.file_services import (
    build_rules_json,
    build_rules_csv,
    build_rules_json_v2,
)
from typing import Dict
from datetime import datetime
from libs.queries import create_update_temp_rules_table_query, create_file_entry_query
from libs.storage_services import upload_blob_to_storage
from libs.enums import JobStageType, StageStatusType
from libs.utils import update_job_status
from libs.settings import (
    AIRFLOW_DEBUG_MODE,
    AIRFLOW_VAR_JSON_VERSION,
    AIRFLOW_DAGRUN_TIMEOUT,
)

# PostgreSQL connection hook
pg_hook = PostgresHook(
    postgres_conn_id="postgres_db_conn",
    options=f"-c statement_timeout={float(AIRFLOW_DAGRUN_TIMEOUT) * 60 * 1000}ms",
)


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
    file_type = validated_params["file_type"]

    # Map file types to temp table suffixes
    if file_type in ["application/json_v1", "application/json_v2"]:
        temp_table_suffix = "json"
    elif file_type == "csv":
        temp_table_suffix = "csv"
    else:
        temp_table_suffix = file_type

    try:
        #  Create or update the temp table with the processed rules data
        pg_hook.run(
            create_update_temp_rules_table_query
            % {
                "scan_report_id": scan_report_id,
                "file_type": temp_table_suffix,
            },
        )
    except Exception as e:
        logging.error(f"Error creating or updating the temp table: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            stage=JobStageType.DOWNLOAD_RULES,
            status=StageStatusType.FAILED,
            details=f"Error creating or updating the temp table: {str(e)}",
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
    json_version = validated_params.get(
        "json_version", "v1"
    )  # default to v1 if not specified

    try:
        # Setup file config. (Credit: @AndyRae)
        file_handlers: Dict[str, FileHandlerConfig] = {
            "csv": FileHandlerConfig(
                lambda: build_rules_csv(scan_report_id),
                "mapping_csv",
                "csv",
            ),
            "application/json_v1": FileHandlerConfig(
                lambda: build_rules_json(scan_report_name, scan_report_id),
                "mapping_json",
                "json",
            ),
            "application/json_v2": FileHandlerConfig(
                lambda: build_rules_json_v2(scan_report_name, scan_report_id),
                "mapping_json_v2",
                "json",
            ),
            "json": FileHandlerConfig(
                lambda: (
                    build_rules_json_v2(scan_report_name, scan_report_id)
                    if AIRFLOW_VAR_JSON_VERSION == "v2"
                    else build_rules_json(scan_report_name, scan_report_id)
                ),
                (
                    "mapping_json_v2"
                    if AIRFLOW_VAR_JSON_VERSION == "v2"
                    else "mapping_json"
                ),
                "json",
            ),
        }
        config = file_handlers[file_type]

        # Generate it
        file = config.handler()
        file_type_value = config.file_type_value
        file_extension = config.file_extension

        # build file name
        if file_type in ["application/json_v1", "application/json_v2"]:
            version = "V1" if file_type == "application/json_v1" else "V2"
            filename = f"Rules - {scan_report_name} - {scan_report_id} - {version} - {datetime.now()}.{file_extension}"
        else:
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

            if AIRFLOW_DEBUG_MODE == "true":
                return
            # Clean up
            pg_hook.run(
                "DROP TABLE IF EXISTS temp_rules_export_%(scan_report_id)s_%(file_type)s"
                % {
                    "scan_report_id": scan_report_id,
                    "file_type": (
                        "json"
                        if file_type in ["application/json_v1", "application/json_v2"]
                        else file_type
                    ),
                }
            )
        except Exception as e:
            logging.error(f"Error creating file entry: {str(e)}")
            update_job_status(
                scan_report=scan_report_id,
                stage=JobStageType.DOWNLOAD_RULES,
                status=StageStatusType.FAILED,
                details="Export rules file failed: {str(e)}",
            )
            raise e
    except Exception as e:
        logging.error(f"Error building and uploading rules file: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            stage=JobStageType.DOWNLOAD_RULES,
            status=StageStatusType.FAILED,
            details=f"Export rules file failed: {str(e)}",
        )
        raise e

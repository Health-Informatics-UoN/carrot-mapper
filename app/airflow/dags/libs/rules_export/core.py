import logging
from libs.utils import pull_validated_params
from airflow.providers.postgres.hooks.postgres import PostgresHook
from libs.types import FileHandlerConfig
from libs.rules_export.file_services import build_rules_json, build_rules_csv
from typing import Dict
from datetime import datetime
from libs.queries import create_update_temp_rules_table_query

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def process_rules_export(**kwargs) -> None:
    """
    Wrapper function for the rules export processing task using openpyxl

    Args:
        context: Airflow context containing task information

    Returns:
        None
    """

    validated_params = pull_validated_params(kwargs, "validate_params_rules_export")
    scan_report_id = validated_params["scan_report_id"]
    scan_report_name = validated_params["scan_report_name"]
    user_id = validated_params["user_id"]
    file_type = validated_params["file_type"]
    #  Create or update the temp table with the processed rules data
    pg_hook.run(
        create_update_temp_rules_table_query,
        parameters={"scan_report_id": scan_report_id},
    )

    # Setup file config
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

    # Save to blob
    filename = f"Rules - {scan_report_name} - {scan_report_id} - {datetime.now()}.{file_extension}"

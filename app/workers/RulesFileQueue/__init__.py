import io
import json
import os
from datetime import datetime
from io import BytesIO
from typing import Dict

import azure.functions as func
from shared_code.models import FileHandlerConfig, RulesFileMessage

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shared_code.django_settings")
import django

django.setup()

from django.db.models.query import QuerySet
from shared.files.models import FileDownload, FileType
from shared.mapping.models import MappingRule, ScanReport
from shared.services.rules_export import (
    get_mapping_rules_as_csv,
    get_mapping_rules_json,
    make_dag,
)
from shared.services.storage_service import StorageService, STORAGE_TYPE
from shared_code.db import JobStageType, StageStatusType, update_job

storage_service = StorageService()


def create_json_rules(rules: QuerySet[MappingRule]) -> BytesIO:
    """
    Converts a queryset of mapping rules into a JSON byte stream.

    Args:
        rules (QuerySet[MappingRule]): A queryset containing mapping rules.

    Returns:
        BytesIO: A byte stream of JSON mapping rules.
    """
    data = get_mapping_rules_json(rules)
    json_data = json.dumps(data, indent=6)
    json_bytes = BytesIO(json_data.encode("utf-8"))
    json_bytes.seek(0)
    return json_bytes


def create_csv_rules(rules: QuerySet[MappingRule]) -> BytesIO:
    """
    Converts a queryset of mapping rules into a CSV byte stream.

    Args:
        rules (QuerySet[MappingRule]): A queryset containing mapping rules.

    Returns:
        BytesIO: A byte stream of CSV mapping rules.
    """
    data = get_mapping_rules_as_csv(rules)
    return io.BytesIO(data.getvalue().encode("utf-8"))


def create_svg_rules(rules: QuerySet[MappingRule]) -> BytesIO:
    """
    Converts a queryset of mapping rules into a SVG byte stream.

    Args:
        rules (QuerySet[MappingRule]): A queryset containing mapping rules.

    Returns:
        BytesIO: A byte stream of SVG DAG mapping rules.
    """
    data = get_mapping_rules_json(rules)
    dag = make_dag(data["cdm"])
    svg_bytes = dag.encode("utf-8")
    return BytesIO(svg_bytes)


def main(msg: func.QueueMessage) -> None:
    """
    Creates and uploads a file for a set of Scan Report Rules.

    The file can be json, csv, or svg.

    Args:
        msg (func.QueueMessage): The message received from the queue.
    """
    # Unwrap message
    msg_body: RulesFileMessage = json.loads(msg.get_body().decode("utf-8"))
    scan_report_id = msg_body.get("scan_report_id")
    scan_report_name = msg_body.get("scan_report_name")
    user_id = msg_body.get("user_id")
    file_type = msg_body.get("file_type")
    # Get all rules for the scan report
    rules = MappingRule.objects.filter(scan_report__id=scan_report_id).all()

    # Setup file config
    file_handlers: Dict[str, FileHandlerConfig] = {
        "text/csv": FileHandlerConfig(
            lambda rules: create_csv_rules(rules), "mapping_csv", "csv"
        ),
        "application/json": FileHandlerConfig(
            lambda rules: create_json_rules(rules), "mapping_json", "json"
        ),
        "image/svg+xml": FileHandlerConfig(
            lambda rules: create_svg_rules(rules), "mapping_svg", "svg"
        ),
    }

    if file_type not in file_handlers:
        update_job(
            JobStageType.DOWNLOAD_RULES,
            StageStatusType.FAILED,
            scan_report=ScanReport.objects.get(id=scan_report_id),
            details=f"Unsupported file type: {file_type}",
        )
        raise ValueError(f"Unsupported file type: {file_type}")

    config = file_handlers[file_type]

    # Generate it
    file = config.handler(rules)
    file_type_value = config.file_type_value
    file_extension = config.file_extension

    # Save to blob
    filename = f"Rules - {scan_report_name} - {scan_report_id} - {datetime.now()}.{file_extension}"

    # Upload the file to rules-exports container
    storage_service.upload_file(
        file_name=filename,
        container="rules-exports",
        file=file,
        content_type=file_type,
        use_minio_bytesio_method=(storage_service._storage_type == STORAGE_TYPE.MINIO),
        use_read_method=(storage_service._storage_type == STORAGE_TYPE.AZURE),
    )

    # create entity
    file_type_entity = FileType.objects.get(value=file_type_value)
    file_entity = FileDownload.objects.create(
        name=filename,
        scan_report_id=scan_report_id,
        user_id=user_id,
        file_type=file_type_entity,
        file_url=filename,
    )
    file_entity.save()
    # update job status
    update_job(
        JobStageType.DOWNLOAD_RULES,
        StageStatusType.COMPLETE,
        scan_report=ScanReport.objects.get(id=scan_report_id),
    )

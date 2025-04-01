import io
import json
import os
import uuid
import logging
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
from shared.services.storage_service import StorageService
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


async def main(req: func.HttpRequest, msg: func.Out[str]) -> func.HttpResponse:
    logging.info("Received request for rules download.")
    
    # try:
    msg_body = req.get_json()
    logging.info(f"Received message: {json.dumps(msg_body, indent=2)}")

    # Create a unique instance ID
    instance_id = str(uuid.uuid4())
    msg_body["instance_id"] = instance_id

    # Unwrap message details
    scan_report_id = msg_body.get("scan_report_id")
    user_id = msg_body.get("user_id")
    file_type = msg_body.get("file_type")

    logging.info(f"Instance ID: {instance_id}")
    logging.info(f"Scan report ID: {scan_report_id}")
    logging.info(f"User ID: {user_id}")
    logging.info(f"File type: {file_type}")

    # Validate input parameters
    if not scan_report_id or not user_id or not file_type:
        logging.error("Missing required parameters: scan_report_id, user_id, or file_type.")
        return func.HttpResponse(
            json.dumps({"error": "Missing required parameters."}),
            status_code=400,
            mimetype="application/json",
        )

    # Get models for this Scan Report
    logging.info("Fetching ScanReport object from database.")
    scan_report = ScanReport.objects.get(id=scan_report_id)
    logging.info(f"ScanReport found: {scan_report}")

    logging.info("Fetching MappingRules for ScanReport.")
    rules = MappingRule.objects.filter(scan_report__id=scan_report_id).all()
    logging.info(f"Found {rules.count()} MappingRules.")

    # File generation handlers
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
        error_message = f"Unsupported file type: {file_type}"
        logging.error(error_message)
        update_job(
            JobStageType.DOWNLOAD_RULES,
            StageStatusType.FAILED,
            scan_report=scan_report,
            details=error_message,
        )
        return func.HttpResponse(json.dumps({"error": error_message}), status_code=400)

    config = file_handlers[file_type]

    # Generate file
    logging.info(f"Generating file for type: {file_type}")
    file = config.handler(rules)
    file_type_value = config.file_type_value
    file_extension = config.file_extension

    filename = f"Rules - {scan_report.dataset} - {scan_report_id} - {datetime.now().isoformat()}.{file_extension}"
    logging.info(f"Generated file: {filename}")

    # Upload file to storage
    logging.info("Uploading file to Azure Blob Storage...")
    storage_service.upload_blob(
        filename, "rules-exports", file, file_type, use_read_method=True
    )
    logging.info("File successfully uploaded.")

    # Create FileDownload entity
    logging.info("Creating FileDownload database entry.")
    file_type_entity = FileType.objects.get(value=file_type_value)
    file_entity = FileDownload.objects.create(
        name=filename,
        scan_report_id=scan_report_id,
        user_id=user_id,
        file_type=file_type_entity,
        file_url=filename,
    )
    file_entity.save()
    logging.info("FileDownload entity saved successfully.")

    # Update job status
    logging.info("Updating job status to COMPLETE.")
    update_job(
        JobStageType.DOWNLOAD_RULES,
        StageStatusType.COMPLETE,
        scan_report=scan_report,
    )

    # Send message to queue
    msg.set(json.dumps(msg_body))
    logging.info("Message sent to queue.")

    return func.HttpResponse(
        json.dumps({"instanceId": instance_id}),
        status_code=202,
        mimetype="application/json",
    )


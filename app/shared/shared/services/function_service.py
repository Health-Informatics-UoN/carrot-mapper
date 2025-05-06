from requests.auth import HTTPBasicAuth
import logging
from urllib.parse import urljoin
import requests
from enum import StrEnum
from typing import Optional
from shared.mapping.models import ScanReport, ScanReportTable
from shared.jobs.models import Job, JobStage, StageStatus
from shared.services.field_vocab_mappings import get_field_vocab_mappings
from shared.services.rules import (
    delete_mapping_rules,
)
from django.conf import settings
from typing import Dict, Any
from shared.services.azurequeue import add_message


class FUNCTION_TYPE(StrEnum):
    AZURE = "azure"
    AIRFLOW = "airflow"


logger = logging.getLogger("test_logger")


class FunctionService:
    def __init__(self):
        """
        Service for triggering functions.
        """
        self._function_type = settings.FUNCTION_TYPE
        self._airflow_base_url = settings.AIRFLOW_URL

    def trigger_auto_mapping(
        self,
        scan_report: ScanReport,
        table: ScanReportTable,
        data_dictionary_name: Optional[str] = None,
        # Placeholder for the issue #623 or enabling users to disable/enable reuse concepts function
        trigger_reuse_concepts: bool = True,
        # TODO: add death_table config here
    ):
        """
        Trigger the automapping process.
        """
        if self._function_type == FUNCTION_TYPE.AZURE:
            # Delete the current mapping rules
            delete_mapping_rules(table.pk)
            # Send request to functions
            msg = {
                "scan_report_id": scan_report.pk,
                "table_id": table.pk,
                "data_dictionary_blob": data_dictionary_name,
            }
            base_url = f"{settings.WORKERS_URL}"
            trigger = f"/api/orchestrators/{settings.WORKERS_RULES_NAME}?code={settings.WORKERS_RULES_KEY}"
            try:
                # Then send the request to workers, in case there is error, the Job record was created already
                response = requests.post(urljoin(base_url, trigger), json=msg)
                response.raise_for_status()

            except requests.exceptions.HTTPError as e:
                logging.error(f"HTTP Trigger failed: {e}")

        elif self._function_type == FUNCTION_TYPE.AIRFLOW:
            # choose the correct trigger for the auto mapping workflow
            auto_mapping_trigger = (
                f"dags/{settings.AIRFLOW_AUTO_MAPPING_DAG_ID}/dagRuns"
            )
            # form the body for POST request
            body = {
                "conf": {
                    "parent_dataset_id": scan_report.parent_dataset.pk,
                    "scan_report_id": scan_report.pk,
                    "table_id": table.pk,
                    "person_id_field": table.person_id.pk,
                    "date_event_field": table.date_event.pk,
                    "field_vocab_pairs": get_field_vocab_mappings(
                        data_dictionary_name, table
                    ),
                    "trigger_reuse_concepts": trigger_reuse_concepts,
                }
            }
            try:
                # Then send the request to workers, in case there is error, the Job record was created already
                response = requests.post(
                    urljoin(self._airflow_base_url, auto_mapping_trigger),
                    json=body,
                    auth=HTTPBasicAuth(
                        settings.AIRFLOW_ADMIN_USERNAME, settings.AIRFLOW_ADMIN_PASSWORD
                    ),
                )
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logging.error(f"HTTP Trigger failed: {e}")

        else:
            raise ValueError(
                "Function type not supported. Only Airflow or Azure Function is supported."
            )

    def trigger_scan_report_processing(
        self,
        message_body: Dict[str, Any],
    ):
        """
        Trigger the scan report processing process.
        """
        if self._function_type == FUNCTION_TYPE.AZURE:
            add_message(settings.WORKERS_UPLOAD_NAME, message_body)

        elif self._function_type == FUNCTION_TYPE.AIRFLOW:
            # choose the correct trigger for the auto mapping workflow
            scan_report_processing_trigger = (
                f"dags/{settings.AIRFLOW_SCAN_REPORT_PROCESSING_DAG_ID}/dagRuns"
            )
            # form the body for POST request
            body = {"conf": message_body}
            try:
                # Then send the request to workers, in case there is error, the Job record was created already
                response = requests.post(
                    urljoin(self._airflow_base_url, scan_report_processing_trigger),
                    json=body,
                    auth=HTTPBasicAuth(
                        settings.AIRFLOW_ADMIN_USERNAME, settings.AIRFLOW_ADMIN_PASSWORD
                    ),
                )
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logging.error(f"HTTP Trigger failed: {e}")

        else:
            raise ValueError(
                "Function type not supported. Only Airflow or Azure Function is supported."
            )

    def trigger_rules_export(
        self,
        message_body: Dict[str, Any],
    ):
        """
        Trigger the rules export process.
        """
        if self._function_type == FUNCTION_TYPE.AZURE:
            add_message(settings.WORKERS_RULES_EXPORT_NAME, message_body)

        elif self._function_type == FUNCTION_TYPE.AIRFLOW:
            # choose the correct trigger for the auto mapping workflow
            rules_export_trigger = (
                f"dags/{settings.AIRFLOW_RULES_EXPORT_DAG_ID}/dagRuns"
            )
            # form the body for POST request
            body = {"conf": message_body}
            try:
                # Then send the request to workers, in case there is error, the Job record was created already
                response = requests.post(
                    urljoin(self._airflow_base_url, rules_export_trigger),
                    json=body,
                    auth=HTTPBasicAuth(
                        settings.AIRFLOW_ADMIN_USERNAME, settings.AIRFLOW_ADMIN_PASSWORD
                    ),
                )
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logging.error(f"HTTP Trigger failed: {e}")

        else:
            raise ValueError(
                "Function type not supported. Only Airflow or Azure Function is supported."
            )

from requests.auth import HTTPBasicAuth
import logging
from urllib.parse import urljoin
import requests
from enum import StrEnum
from typing import Optional, Dict, Any, Union
from shared.mapping.models import ScanReport, ScanReportTable
from shared.services.field_vocab_mappings import get_field_vocab_mappings
from shared.services.rules import delete_mapping_rules
from django.conf import settings
from shared.services.azurequeue import add_message


class FUNCTION_TYPE(StrEnum):
    AZURE = "azure"
    AIRFLOW = "airflow"


class FunctionService:
    def __init__(self):
        """
        Service for triggering functions.
        """
        self._function_type = settings.FUNCTION_TYPE
        self._airflow_base_url = settings.AIRFLOW_URL

    def _validate_function_type(self):
        """Validate that function type is supported."""
        if self._function_type not in (FUNCTION_TYPE.AZURE, FUNCTION_TYPE.AIRFLOW):
            raise ValueError(
                "Function type not supported. Only Airflow or Azure Function is supported."
            )

    def _trigger_airflow_dag(
        self, dag_id: str, payload: Dict[str, Any]
    ) -> requests.Response:
        """Common method to trigger Airflow DAGs."""
        endpoint = f"dags/{dag_id}/dagRuns"
        body = {"conf": payload}

        try:
            response = requests.post(
                urljoin(self._airflow_base_url, endpoint),
                json=body,
                auth=HTTPBasicAuth(
                    settings.AIRFLOW_ADMIN_USERNAME, settings.AIRFLOW_ADMIN_PASSWORD
                ),
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP Trigger failed: {e}")
            raise

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
        self._validate_function_type()

        if self._function_type == FUNCTION_TYPE.AZURE:
            # Delete the current mapping rules
            delete_mapping_rules(table.pk)

            # Send request to functions
            msg = {
                "scan_report_id": scan_report.pk,
                "table_id": table.pk,
                "data_dictionary_blob": data_dictionary_name,
            }
            base_url = settings.WORKERS_URL
            trigger = f"/api/orchestrators/{settings.WORKERS_RULES_NAME}?code={settings.WORKERS_RULES_KEY}"

            try:
                response = requests.post(urljoin(base_url, trigger), json=msg)
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logging.error(f"HTTP Trigger failed: {e}")

        elif self._function_type == FUNCTION_TYPE.AIRFLOW:
            payload = {
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

            try:
                self._trigger_airflow_dag(settings.AIRFLOW_AUTO_MAPPING_DAG_ID, payload)
            except requests.exceptions.HTTPError:
                pass

    def trigger_scan_report_processing(self, message_body: Dict[str, Any]):
        """
        Trigger the scan report processing process.
        """
        self._validate_function_type()

        if self._function_type == FUNCTION_TYPE.AZURE:
            add_message(settings.WORKERS_UPLOAD_NAME, message_body)

        elif self._function_type == FUNCTION_TYPE.AIRFLOW:
            try:
                self._trigger_airflow_dag(
                    settings.AIRFLOW_SCAN_REPORT_PROCESSING_DAG_ID, message_body
                )
            except requests.exceptions.HTTPError:
                pass

    def trigger_rules_export(self, message_body: Dict[str, Any]):
        """
        Trigger the rules export process.
        """
        self._validate_function_type()

        if self._function_type == FUNCTION_TYPE.AZURE:
            add_message(settings.WORKERS_RULES_EXPORT_NAME, message_body)

        elif self._function_type == FUNCTION_TYPE.AIRFLOW:
            try:
                self._trigger_airflow_dag(
                    settings.AIRFLOW_RULES_EXPORT_DAG_ID, message_body
                )
            except requests.exceptions.HTTPError:
                pass

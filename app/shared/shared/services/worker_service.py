from requests.auth import HTTPBasicAuth
import logging
from urllib.parse import urljoin
import requests
from typing import Optional, Dict, Any
from shared.mapping.models import ScanReport, ScanReportTable
from shared.services.field_vocab_mappings import get_field_vocab_mappings
from shared.services.rules import delete_mapping_rules
from django.conf import settings
from shared.services.azurequeue import add_message
from abc import ABC, abstractmethod
from shared.enums import WorkerServiceType


class WorkerService(ABC):
    """Abstract base class for worker services."""

    @abstractmethod
    def trigger_auto_mapping(
        self,
        scan_report: ScanReport,
        table: ScanReportTable,
        data_dictionary_name: Optional[str] = None,
        trigger_reuse_concepts: Optional[bool] = True,
    ):
        """Trigger automated mapping process."""
        pass

    @abstractmethod
    def trigger_scan_report_processing(self, message_body: Dict[str, Any]):
        """Trigger scan report processing."""
        pass

    @abstractmethod
    def trigger_rules_export(self, message_body: Dict[str, Any]):
        """Trigger rules export."""
        pass


class AzureWorkerService(WorkerService):
    """Azure Functions implementation of worker service."""

    def __init__(self):
        self._workers_url = settings.WORKERS_URL
        self._workers_rules_name = settings.WORKERS_RULES_NAME
        self._workers_rules_key = settings.WORKERS_RULES_KEY
        self._workers_upload_name = settings.WORKERS_UPLOAD_NAME
        self._workers_rules_export_name = settings.WORKERS_RULES_EXPORT_NAME

    def trigger_auto_mapping(
        self,
        scan_report: ScanReport,
        table: ScanReportTable,
        data_dictionary_name: Optional[str] = None,
        trigger_reuse_concepts: Optional[bool] = True,
    ):
        # Delete the current mapping rules
        delete_mapping_rules(table.pk)

        # Send request to functions
        msg = {
            "scan_report_id": scan_report.pk,
            "table_id": table.pk,
            "data_dictionary_blob": data_dictionary_name,
        }
        trigger = f"/api/orchestrators/{self._workers_rules_name}?code={self._workers_rules_key}"

        try:
            response = requests.post(urljoin(self._workers_url, trigger), json=msg)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP Trigger failed: {e}")

    def trigger_scan_report_processing(self, message_body: Dict[str, Any]):
        add_message(self._workers_upload_name, message_body)

    def trigger_rules_export(self, message_body: Dict[str, Any]):
        add_message(self._workers_rules_export_name, message_body)


class AirflowWorkerService(WorkerService):
    """Airflow implementation of worker service."""

    def __init__(self):
        self._airflow_base_url = settings.AIRFLOW_BASE_URL
        self._workers_upload_name = settings.WORKERS_UPLOAD_NAME
        self._workers_rules_export_name = settings.WORKERS_RULES_EXPORT_NAME
        self._auto_mapping_dag_id = settings.AIRFLOW_AUTO_MAPPING_DAG_ID
        self._scan_report_processing_dag_id = (
            settings.AIRFLOW_SCAN_REPORT_PROCESSING_DAG_ID
        )
        self._rules_export_dag_id = settings.AIRFLOW_RULES_EXPORT_DAG_ID

    def _trigger_airflow_dag(
        self, dag_id: str, payload: Dict[str, Any]
    ) -> requests.Response:
        """Common method to trigger Airflow DAGs through the Airflow REST API."""
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
            logging.error(f"HTTP Trigger failed when triggering DAG {dag_id}: {e}")
            raise requests.exceptions.HTTPError(
                f"Failed to trigger Airflow DAG {dag_id}: {str(e)}"
            ) from e

    def trigger_auto_mapping(
        self,
        scan_report: ScanReport,
        table: ScanReportTable,
        data_dictionary_name: Optional[str] = None,
        # Placeholder for the issue #623 or enabling users to disable/enable reuse concepts function
        trigger_reuse_concepts: bool = True,
        # TODO: add death_table config here
    ):
        payload = {
            "parent_dataset_id": scan_report.parent_dataset.pk,
            "scan_report_id": scan_report.pk,
            "table_id": table.pk,
            "person_id_field": table.person_id.pk,
            "date_event_field": table.date_event.pk,
            "field_vocab_pairs": (
                get_field_vocab_mappings(data_dictionary_name, table)
                if data_dictionary_name
                else []
            ),
            "trigger_reuse_concepts": trigger_reuse_concepts,
        }

        self._trigger_airflow_dag(self._auto_mapping_dag_id, payload)

    def trigger_scan_report_processing(self, message_body: Dict[str, Any]):
        self._trigger_airflow_dag(self._scan_report_processing_dag_id, message_body)

    def trigger_rules_export(self, message_body: Dict[str, Any]):
        self._trigger_airflow_dag(self._rules_export_dag_id, message_body)


# Function to create the appropriate service based on configuration
def get_worker_service() -> WorkerService:
    """Function to create the appropriate worker service."""
    worker_service_type = settings.WORKER_SERVICE_TYPE

    if worker_service_type == WorkerServiceType.AZURE:
        return AzureWorkerService()
    elif worker_service_type == WorkerServiceType.AIRFLOW:
        return AirflowWorkerService()
    else:
        raise ValueError(
            "Worker service type not supported. Only `airflow` or `azure` is supported."
        )

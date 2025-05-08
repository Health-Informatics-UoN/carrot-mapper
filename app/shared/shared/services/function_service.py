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
    """
    Service for triggering background processing functions in different environments.

    This service abstracts the implementation details of triggering data processing
    workflows in either Azure Functions or Apache Airflow environments. It provides
    a consistent interface for initiating common operations like auto-mapping,
    scan report processing, and rules export regardless of the underlying execution platform.

    The service determines which platform to use based on the FUNCTION_TYPE setting
    and handles the appropriate API calls or message queue operations accordingly.
    """

    def __init__(self):
        """
        Initialize the FunctionService with configuration from Django settings.

        Sets up the service with the configured function type (Azure or Airflow)
        and the base URL for Airflow API calls if applicable.
        """
        self._function_type = settings.FUNCTION_TYPE
        self._airflow_base_url = settings.AIRFLOW_URL

    def _validate_function_type(self):
        """
        Validate that the configured function type is supported.

        Raises:
            ValueError: If the function type is not one of the supported types
                       (currently Azure or Airflow).
        """
        if self._function_type not in (FUNCTION_TYPE.AZURE, FUNCTION_TYPE.AIRFLOW):
            raise ValueError(
                "Function type not supported. Only Airflow or Azure Function is supported."
            )

    def _trigger_airflow_dag(
        self, dag_id: str, payload: Dict[str, Any]
    ) -> requests.Response:
        """
        Common method to trigger Airflow DAGs through the Airflow REST API.

        Args:
            dag_id: The ID of the DAG to trigger in Airflow.
            payload: The configuration data to pass to the DAG run.

        Returns:
            requests.Response: The HTTP response object from the Airflow API call.

        Raises:
            requests.exceptions.HTTPError: If the HTTP request to Airflow fails.
        """
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
        Trigger the automated mapping process for a scan report table.

        This function initiates the process that automatically maps table fields
        to standardized concepts based on the available metadata and configurations.

        Args:
            scan_report: The ScanReport object containing the table to be mapped.
            table: The specific ScanReportTable to be mapped.
            data_dictionary_name: Optional name of a data dictionary blob to use
                                 for field vocabulary mappings.
            trigger_reuse_concepts: Flag to enable/disable the reuse of previously
                                   mapped concepts (default: True).

        Raises:
            ValueError: If the configured function type is not supported.
            HTTPError: If the HTTP request to trigger the process fails.
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
            # TODO: make the method to add_message here to solve the issue #996
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
                "field_vocab_pairs": (
                    get_field_vocab_mappings(data_dictionary_name, table)
                    if data_dictionary_name
                    else []
                ),
                "trigger_reuse_concepts": trigger_reuse_concepts,
            }

            self._trigger_airflow_dag(settings.AIRFLOW_AUTO_MAPPING_DAG_ID, payload)

    def trigger_scan_report_processing(self, message_body: Dict[str, Any]):
        """
        Trigger the processing of a scan report.

        This function initiates the processing workflow for a scan report,
        which typically involves parsing, validation, and initial data preparation.

        Args:
            message_body: A dictionary containing all necessary parameters for
                         processing the scan report, such as file locations,
                         processing options, and identifiers.

        """
        self._validate_function_type()

        if self._function_type == FUNCTION_TYPE.AZURE:
            add_message(settings.WORKERS_UPLOAD_NAME, message_body)

        elif self._function_type == FUNCTION_TYPE.AIRFLOW:
            # Use the same message body for both Azure and Airflow for now, until the function in Airlfow is implemented
            add_message(settings.WORKERS_UPLOAD_NAME, message_body)
            # self._trigger_airflow_dag(
            #     settings.AIRFLOW_SCAN_REPORT_PROCESSING_DAG_ID, message_body
            # )

    def trigger_rules_export(self, message_body: Dict[str, Any]):
        """
        Trigger the export of mapping rules.

        This function initiates the process to export mapping rules, which
        typically involves generating standardized output files that define
        how source data fields map to target concepts or structures.

        Args:
            message_body: A dictionary containing all necessary parameters for
                         the export process, such as identifiers for the rules
                         to export and output format specifications.

        """
        self._validate_function_type()

        if self._function_type == FUNCTION_TYPE.AZURE:
            add_message(settings.WORKERS_RULES_EXPORT_NAME, message_body)

        elif self._function_type == FUNCTION_TYPE.AIRFLOW:
            # Use the same message body for both Azure and Airflow for now, until the function in Airlfow is implemented
            add_message(settings.WORKERS_RULES_EXPORT_NAME, message_body)
            # self._trigger_airflow_dag(
            #     settings.AIRFLOW_RULES_EXPORT_DAG_ID, message_body
            # )

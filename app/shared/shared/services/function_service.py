from requests.auth import HTTPBasicAuth
import logging
import os
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


class FUNCTION_TYPE(StrEnum):
    AZURE = "azure"
    AIRFLOW = "airflow"


logger = logging.getLogger("test_logger")


class FunctionService:
    def __init__(self):
        """
        Service for triggering functions.
        """
        self._function_type = os.getenv("FUNCTION_TYPE")

    def trigger_auto_mapping(
        self,
        scan_report: ScanReport,
        table: ScanReportTable,
        data_dictionary_name: Optional[str] = None,
        trigger_reuse_concepts: bool = True,
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
            base_url = f"{os.getenv('WORKERS_URL')}"
            trigger = f"/api/orchestrators/{os.getenv('WORKERS_RULES_NAME')}?code={os.getenv('WORKERS_RULES_KEY')}"
            try:
                # Then send the request to workers, in case there is error, the Job record was created already
                response = requests.post(urljoin(base_url, trigger), json=msg)
                response.raise_for_status()

            except requests.exceptions.HTTPError as e:
                logging.error(f"HTTP Trigger failed: {e}")

        elif self._function_type == FUNCTION_TYPE.AIRFLOW:
            # TODO: add update Generate rules to avoid UI breaking
            # TODO: make sub functions for each step
            # TODO: make auth configurable for airflow
            # TODO: what if I don't have DD but want to update the person ID and date event?
            # TODO: refresh the mapping rules for manual mapping or for the table without field-vocab pairs or for a SR doesn't have reuse demand
            base_url = f"{os.getenv('AIRFLOW_URL')}"
            # Send to functions
            if data_dictionary_name or get_field_vocab_mappings(
                data_dictionary_name, table
            ):
                vocab_concepts_msg = {
                    "conf": {
                        "scan_report_id": scan_report.pk,
                        "table_id": table.pk,
                        "person_id_field": table.person_id.pk,
                        "date_event_field": table.date_event.pk,
                        "field_vocab_pairs": get_field_vocab_mappings(
                            data_dictionary_name, table
                        ),
                    }
                }
                vocab_concepts_trigger = (
                    f"/api/v1/dags/{os.getenv('AIRFLOW_VOCAB_CONCEPTS_DAG_ID')}/dagRuns"
                )
                try:
                    # Then send the request to workers, in case there is error, the Job record was created already
                    response = requests.post(
                        urljoin(base_url, vocab_concepts_trigger),
                        json=vocab_concepts_msg,
                        auth=HTTPBasicAuth(
                            os.getenv("AIRFLOW_USERNAME"), os.getenv("AIRFLOW_PASSWORD")
                        ),
                    )
                    response.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    logging.error(f"HTTP Trigger failed: {e}")
            else:
                Job.objects.create(
                    scan_report=scan_report,
                    scan_report_table=table,
                    stage=JobStage.objects.get(value="BUILD_CONCEPTS_FROM_DICT"),
                    status=StageStatus.objects.get(value="COMPLETE"),
                    details=f"Skipped, because no data dictionary provided or no vocab ID is set for the table {table.name}.",
                )

            if trigger_reuse_concepts:
                reuse_concepts_msg = {
                    "conf": {
                        "parent_dataset_id": scan_report.parent_dataset.pk,
                        "scan_report_id": scan_report.pk,
                        "table_id": table.pk,
                        "person_id_field": table.person_id.pk,
                        "date_event_field": table.date_event.pk,
                        "has_data_dictionary": True if data_dictionary_name else False,
                    }
                }
                reuse_concepts_trigger = (
                    f"/api/v1/dags/{os.getenv('AIRFLOW_REUSE_CONCEPTS_DAG_ID')}/dagRuns"
                )
                try:
                    # Then send the request to workers, in case there is error, the Job record was created already
                    response = requests.post(
                        urljoin(base_url, reuse_concepts_trigger),
                        json=reuse_concepts_msg,
                        auth=HTTPBasicAuth(
                            os.getenv("AIRFLOW_USERNAME"), os.getenv("AIRFLOW_PASSWORD")
                        ),
                    )
                    response.raise_for_status()

                except requests.exceptions.HTTPError as e:
                    logging.error(f"HTTP Trigger failed: {e}")
            else:
                Job.objects.create(
                    scan_report=scan_report,
                    scan_report_table=table,
                    stage=JobStage.objects.get(value="REUSE_CONCEPTS"),
                    status=StageStatus.objects.get(value="COMPLETE"),
                    details=f"Skipped as specified in the request.",
                )
        else:
            raise ValueError(
                "Function type not supported. Only Airflow or Azure Function is supported."
            )

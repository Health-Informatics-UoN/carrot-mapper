"""
Small helpers shared by the registry_import DAG's steps: constants, names of
things in storage and the database, and reading the ImportJob and run settings.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from airflow.exceptions import AirflowFailException

from libs.db import pg_hook
from libs.registry_import import queries

# Origins with their own source preparation (prepare_source.py). Their values
# are the ids seeded in registry_origin, which validate_params checks against.
CARROT_DIRECT_PUBLISH = "CARROT_DIRECT_PUBLISH"
SSSOM_UPLOAD = "SSSOM_UPLOAD"

# Where notifications link to in the client app.
MAPPING_SET_URL = "/registry/mapping-sets/{mapping_set_id}"
IMPORT_JOB_URL = "/registry/imports/{import_job_id}"


def file_key_for(import_job_id: str) -> str:
    """Blob name of a job's SSSOM file in REGISTRY_SSSOM_CONTAINER."""
    return f"imports/{import_job_id}/original.sssom.tsv"


def temp_rules_table_suffix(import_job_id: str) -> str:
    """
    Suffix of a direct publish's temp rules table: one per job, so concurrent
    publishes (or a rules export) of the same scan report don't share it.
    Postgres truncates names at 63 characters, hence the short form.
    """
    return f"registry_{uuid.UUID(import_job_id).hex[:12]}"


def drop_temp_rules_table(scan_report_id: int, table_suffix: str) -> None:
    try:
        pg_hook.run(
            "DROP TABLE IF EXISTS temp_rules_export_%(scan_report_id)s_%(suffix)s"
            % {"scan_report_id": int(scan_report_id), "suffix": table_suffix}
        )
    except Exception as e:
        logging.error(f"Could not drop temp rules table: {e}")


def get_job(import_job_id: str) -> dict[str, Any]:
    row = pg_hook.get_first(
        queries.get_import_job_query, parameters={"import_job_id": import_job_id}
    )
    if not row:
        raise AirflowFailException(f"ImportJob {import_job_id} does not exist")
    return dict(zip(("id", "status", "origin", "file_key", "submitted_by_id"), row))


def job_file_key(import_job_id: str) -> str:
    """The job's SSSOM file in storage (ImportJob.file_key)."""
    file_key = get_job(import_job_id)["file_key"]
    if not file_key:
        raise AirflowFailException(
            f"ImportJob {import_job_id} has no file_key to import"
        )
    return file_key


def parse_overrides(value: Any) -> dict[str, Any]:
    """The run conf's overrides, as a dict (Airflow may pass it as JSON text)."""
    if value in (None, "", "None"):
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as e:
            raise AirflowFailException(f"overrides is not valid JSON: {e}")
    if not isinstance(value, dict):
        raise AirflowFailException("overrides must be an object")
    return value


def get_license_iri(license_id: str) -> str | None:
    """The license_iri of a registry_license row, None if there is no such id."""
    row = pg_hook.get_first(
        queries.get_license_iri_query, parameters={"license_id": license_id}
    )
    return row[0] if row else None


def file_overrides(params: dict[str, Any]) -> dict[str, Any]:
    """
    The overrides as SSSOM metadata: the request names the license by its
    License id, which the file needs as an IRI (validate_params looked it up).
    """
    overrides = dict(params["overrides"])
    if params.get("license_iri"):
        overrides["license"] = params["license_iri"]
    return overrides

"""Step 1: check the run conf and mark the ImportJob RUNNING."""

from __future__ import annotations

import uuid
from typing import Any

from airflow.exceptions import AirflowFailException

from libs.db import pg_hook
from libs.registry_import import queries
from libs.registry_import.full_validate_checks import IssueLog, normalise_overrides
from libs.registry_import.helpers import (
    CARROT_DIRECT_PUBLISH,
    get_job,
    get_license_iri,
    parse_overrides,
)
from libs.utils import _validate_dag_params

# What a Mapper direct publish must say about the set (the API requires the
# same): Mapper has no set identity of its own to put in the file.
DIRECT_PUBLISH_REQUIRED_OVERRIDES = {
    "mapping_set_id": "set_uri",
    "mapping_set_version": "set_version",
    "mapping_set_title": "title",
    "license": "license",
}


def validate_params_registry_import(**context) -> dict[str, Any]:
    """
    Check the run conf and mark the job RUNNING. The conf, sent by the API:

        import_job_id    ImportJob.id (UUID)
        origin           a registry_origin id: CARROT_DIRECT_PUBLISH | SSSOM_UPLOAD
        user_id          the submitting user
        scan_report_id   CARROT_DIRECT_PUBLISH only
        file_key         SSSOM_UPLOAD only, if not already on the ImportJob
        overrides        set_uri, set_version, title, description, license (a
                         License id), status (DRAFT|PUBLISHED), and
                         include_author_orcid_ids (true/false: write the ORCID
                         iD of each mapping's author as its author_id).
                         CARROT_DIRECT_PUBLISH needs set_uri, set_version,
                         title, license and include_author_orcid_ids; for
                         SSSOM_UPLOAD they're optional and override the file.
        mapper_version   optional, CARROT_DIRECT_PUBLISH only

    Returns the validated parameters (the other steps' XCom input), with
    ``license_iri`` added when a license was given.
    """
    conf = context["dag_run"].conf or {}
    try:
        params = _validate_dag_params(
            int_params=["user_id"],
            string_params=["import_job_id", "origin"],
            **context,
        )
    except ValueError as e:
        raise AirflowFailException(str(e))

    errors = []
    try:
        params["import_job_id"] = str(uuid.UUID(params["import_job_id"]))
    except ValueError:
        errors.append(f"Invalid import_job_id: {params['import_job_id']}")
    origins = sorted(r[0] for r in pg_hook.get_records(queries.get_origins_query))
    if params["origin"] not in origins:
        errors.append(f"Invalid origin: {params['origin']}. Must be one of {origins}")

    overrides = parse_overrides(conf.get("overrides"))
    params["overrides"] = overrides
    params["file_key"] = conf.get("file_key") or ""
    params["mapper_version"] = conf.get("mapper_version")
    params["scan_report_id"] = None
    params["license_iri"] = None

    if params["origin"] == CARROT_DIRECT_PUBLISH:
        try:
            params["scan_report_id"] = int(conf.get("scan_report_id"))
        except (TypeError, ValueError):
            errors.append("CARROT_DIRECT_PUBLISH needs an integer scan_report_id")
        slots, _ = normalise_overrides(overrides, IssueLog(0))
        for slot, name in DIRECT_PUBLISH_REQUIRED_OVERRIDES.items():
            if not slots.get(slot):
                errors.append(f"CARROT_DIRECT_PUBLISH needs overrides.{name}")
        if not isinstance(overrides.get("include_author_orcid_ids"), bool):
            errors.append(
                "CARROT_DIRECT_PUBLISH needs overrides.include_author_orcid_ids "
                "(true or false)"
            )

    license_id = overrides.get("license")
    if license_id:
        params["license_iri"] = get_license_iri(str(license_id))
        if params["license_iri"] is None:
            errors.append(f"Unknown license id: {license_id}")

    if errors:
        raise AirflowFailException("Parameter validation failed: " + "; ".join(errors))

    job = get_job(params["import_job_id"])
    if job["status"] == "SUCCEEDED":
        raise AirflowFailException(f"ImportJob {job['id']} has already succeeded")
    if job["origin"] != params["origin"]:
        raise AirflowFailException(
            f"origin {params['origin']} does not match the ImportJob's {job['origin']}"
        )
    pg_hook.run(
        queries.mark_import_job_running_query,
        parameters={
            "import_job_id": params["import_job_id"],
            "dag_run_id": context["dag_run"].run_id,
        },
    )
    # For SSSOM_UPLOAD: the API's upload endpoint (POST imports/) stores the
    # file and sets ImportJob.file_key itself, but may also pass file_key in the
    # conf. Record it on the job if the job doesn't have one yet, so later steps
    # (which read ImportJob.file_key) find the file. A direct publish has no
    # file_key yet: prepare_source builds the file and sets it.
    if params["file_key"] and not job["file_key"]:
        pg_hook.run(
            queries.set_import_job_file_key_query,
            parameters={
                "import_job_id": params["import_job_id"],
                "file_key": params["file_key"],
            },
        )
    return params

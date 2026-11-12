"""
Airflow task callables for the registry_import DAG (see registry_import_dag.py).

Tasks hand each other only IDs and keys through XCom, never data: the SSSOM
file in storage (ImportJob.file_key) is re-read by each task that needs it.

Problems that retrying can't fix (bad parameters, an invalid file, a set that
already exists) raise AirflowFailException, which fails the task at once
instead of using up its retries.
"""

from __future__ import annotations

import json
import logging
import uuid
from contextlib import closing
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from airflow.exceptions import AirflowFailException

from libs.db import pg_hook
from libs.notifications import NotificationType, create_import_job_notification
from libs.queries import create_update_temp_rules_table_query
from libs.registry_import import queries
from libs.registry_import.load import LoadError, load_plan
from libs.registry_import.parse import decode, parse_sssom
from libs.registry_import.validate import (
    OVERRIDE_SLOTS,
    PUBLISHED,
    ImportPlan,
    IssueLog,
    SetRecord,
    Vocabulary,
    build_import,
    normalise_overrides,
)
from libs.rules_export.file_services import fetch_sssom_rules, get_creator
from libs.rules_export.sssom import write_sssom_tsv
from libs.settings import (
    AIRFLOW_DEBUG_MODE,
    REGISTRY_IMPORT_MAX_ISSUES,
    REGISTRY_SSSOM_CONTAINER,
)
from libs.storage_services import download_blob_to_tmp, upload_blob_to_storage
from libs.utils import _validate_dag_params, pull_validated_params

VALIDATE_PARAMS_TASK = "validate_params_registry_import"

CARROT_DIRECT_PUBLISH = "CARROT_DIRECT_PUBLISH"
SSSOM_UPLOAD = "SSSOM_UPLOAD"
ORIGINS = (CARROT_DIRECT_PUBLISH, SSSOM_UPLOAD)

# Overrides a Mapper direct publish must carry: Mapper has no set identity of
# its own to put in the file.
DIRECT_PUBLISH_REQUIRED_OVERRIDES = {
    "mapping_set_id": "set_uri",
    "mapping_set_version": "set_version",
    "license": "license",
}

# Where notifications link to in the client app.
MAPPING_SET_URL = "/registry/mapping-sets/{mapping_set_id}"
IMPORT_JOB_URL = "/registry/imports/{import_job_id}"


def temp_rules_table_suffix(import_job_id: str) -> str:
    """
    Suffix of a direct publish's temp rules table: one per job, so concurrent
    publishes (or a rules export) of the same scan report don't share it.
    Postgres truncates names at 63 characters, hence the short form.
    """
    return f"registry_{uuid.UUID(import_job_id).hex[:12]}"


def file_key_for(import_job_id: str) -> str:
    """Blob name of a job's SSSOM file in REGISTRY_SSSOM_CONTAINER."""
    return f"imports/{import_job_id}/original.sssom.tsv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_job(import_job_id: str) -> dict[str, Any]:
    row = pg_hook.get_first(
        queries.get_import_job_query, parameters={"import_job_id": import_job_id}
    )
    if not row:
        raise AirflowFailException(f"ImportJob {import_job_id} does not exist")
    return dict(zip(("id", "status", "origin", "file_key", "submitted_by_id"), row))


def _get_vocabulary() -> Vocabulary:
    vocab = Vocabulary(
        predicates={r[0] for r in pg_hook.get_records(queries.get_predicates_query)},
        justifications={
            r[0] for r in pg_hook.get_records(queries.get_justifications_query)
        },
    )
    # Filled by the license_sync DAG from the SPDX License List
    for license_id, license_iri, see_also, is_deprecated in pg_hook.get_records(
        queries.get_licenses_query
    ):
        vocab.add_license(license_id, license_iri, see_also, is_deprecated)
    return vocab


def _license_ids_to_iris(
    overrides: dict[str, Any], vocab: Vocabulary
) -> dict[str, Any]:
    """
    Accept a License id (e.g. "CC-BY-4.0") as the license override as well as
    its IRI: SSSOM wants the IRI.
    """
    license_value = overrides.get("license")
    if license_value in vocab.license_iris:
        return {**overrides, "license": vocab.license_iris[license_value]}
    return overrides


def _include_orcid_ids(overrides: dict[str, Any]) -> bool:
    """Whether the user opted in to publishing their ORCID iD (default: no)."""
    value = overrides.get("include_orcid_ids", False)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return bool(value)


def _parse_overrides(value: Any) -> dict[str, Any]:
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


def _build_plan(params: dict[str, Any], file_key: str) -> ImportPlan:
    """Download the job's SSSOM file, and validate and normalise all of it."""
    vocab = _get_vocabulary()
    local_path: Path = download_blob_to_tmp(REGISTRY_SSSOM_CONTAINER, file_key)
    try:
        data = local_path.read_bytes()
    finally:
        local_path.unlink(missing_ok=True)

    text, decode_issues = decode(data)
    if text is None:
        log = IssueLog(REGISTRY_IMPORT_MAX_ISSUES)
        for issue in decode_issues:
            log.add(issue)
        return ImportPlan(SetRecord(), [], log)

    parsed = parse_sssom(text)
    parsed.issues[:0] = decode_issues
    plan = build_import(
        parsed,
        vocab,
        _license_ids_to_iris(params["overrides"], vocab),
        max_issues=REGISTRY_IMPORT_MAX_ISSUES,
    )
    if plan.mapping_set.set_uri and plan.mapping_set.set_version:
        conflict = pg_hook.get_first(
            queries.get_conflicting_set_query,
            parameters={
                "set_uri": plan.mapping_set.set_uri,
                "set_version": plan.mapping_set.set_version,
                "import_job_id": params["import_job_id"],
            },
        )
        if conflict:
            plan.issues.error(
                "set_version_exists",
                f"Mapping set {plan.mapping_set.set_uri} version "
                f"{plan.mapping_set.set_version} already exists; publish "
                "corrections as a new mapping_set_version",
                column="mapping_set_version",
            )
    return plan


def _job_file_key(params: dict[str, Any]) -> str:
    job = _get_job(params["import_job_id"])
    if not job["file_key"]:
        raise AirflowFailException(
            f"ImportJob {params['import_job_id']} has no file_key to import"
        )
    return job["file_key"]


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


def validate_params_registry_import(**context) -> dict[str, Any]:
    """
    Check the run conf and mark the job RUNNING. The conf, sent by the API:

        import_job_id    ImportJob.id (UUID)
        origin           CARROT_DIRECT_PUBLISH | SSSOM_UPLOAD
        user_id          the submitting user
        scan_report_id   CARROT_DIRECT_PUBLISH only
        file_key         SSSOM_UPLOAD only, if not already on the ImportJob
        overrides        optional: set_uri, set_version, title, description,
                         license (IRI or License id), status (DRAFT|PUBLISHED),
                         include_orcid_ids (CARROT_DIRECT_PUBLISH: write the
                         user's ORCID iD as creator_id; default false).
                         CARROT_DIRECT_PUBLISH needs set_uri, set_version and
                         license.
        mapper_version   optional, CARROT_DIRECT_PUBLISH only
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
    if params["origin"] not in ORIGINS:
        errors.append(f"Invalid origin: {params['origin']}. Must be one of {ORIGINS}")

    overrides = _parse_overrides(conf.get("overrides"))
    params["overrides"] = overrides
    params["file_key"] = conf.get("file_key") or ""
    params["mapper_version"] = conf.get("mapper_version")
    params["scan_report_id"] = None
    if params["origin"] == CARROT_DIRECT_PUBLISH:
        try:
            params["scan_report_id"] = int(conf.get("scan_report_id"))
        except (TypeError, ValueError):
            errors.append("CARROT_DIRECT_PUBLISH needs an integer scan_report_id")
        slots, _ = normalise_overrides(overrides, IssueLog(0))
        for slot, name in DIRECT_PUBLISH_REQUIRED_OVERRIDES.items():
            if not slots.get(slot):
                errors.append(f"CARROT_DIRECT_PUBLISH needs overrides.{name}")
    if errors:
        raise AirflowFailException("Parameter validation failed: " + "; ".join(errors))

    job = _get_job(params["import_job_id"])
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
    if params["file_key"] and not job["file_key"]:
        pg_hook.run(
            queries.set_import_job_file_key_query,
            parameters={
                "import_job_id": params["import_job_id"],
                "file_key": params["file_key"],
            },
        )
    return params


def prepare_source(**kwargs) -> str:
    """
    Make sure the job's SSSOM file is in storage. An upload is there already;
    a Mapper direct publish builds it from the scan report's mappings with the
    rules SSSOM exporter, adding the set identity from the overrides.
    """
    params = pull_validated_params(kwargs, VALIDATE_PARAMS_TASK)
    if params["origin"] == SSSOM_UPLOAD:
        file_key = _job_file_key(params)
        logging.info(f"SSSOM upload: using stored file {file_key}")
        return file_key
    return _build_direct_publish_file(params)


def _build_direct_publish_file(params: dict[str, Any]) -> str:
    import_job_id = params["import_job_id"]
    scan_report_id = params["scan_report_id"]
    vocab = _get_vocabulary()
    slots, _ = normalise_overrides(
        _license_ids_to_iris(params["overrides"], vocab), IssueLog(0)
    )
    if not slots.get("mapping_set_title"):
        row = pg_hook.get_first(
            queries.get_scan_report_name_query,
            parameters={"scan_report_id": scan_report_id},
        )
        if not row:
            raise AirflowFailException(f"Scan report {scan_report_id} does not exist")
        slots["mapping_set_title"] = row[0]

    table_suffix = temp_rules_table_suffix(import_job_id)
    try:
        pg_hook.run(
            create_update_temp_rules_table_query
            % {"scan_report_id": scan_report_id, "file_type": table_suffix}
        )
        rules = fetch_sssom_rules(scan_report_id, table_suffix)
        if not rules:
            raise AirflowFailException(
                f"Scan report {scan_report_id} has no mappings to publish"
            )
        creator_username, creator_orcid = get_creator(params["user_id"])
        if not _include_orcid_ids(params["overrides"]):
            creator_orcid = None
        tsv = write_sssom_tsv(
            rules,
            created=datetime.now(UTC),
            mapper_version=params.get("mapper_version"),
            creator_username=creator_username,
            creator_orcid=creator_orcid,
            set_metadata={
                k: v for k, v in slots.items() if k in OVERRIDE_SLOTS.values()
            },
        )
    finally:
        if AIRFLOW_DEBUG_MODE != "true":
            _drop_temp_rules_table(scan_report_id, table_suffix)

    file_key = file_key_for(import_job_id)
    upload_blob_to_storage(
        container_name=REGISTRY_SSSOM_CONTAINER,
        blob_name=file_key,
        data=BytesIO(tsv.encode("utf-8")),
        content_type="text/tab-separated-values",
    )
    pg_hook.run(
        queries.set_import_job_file_key_query,
        parameters={"import_job_id": import_job_id, "file_key": file_key},
    )
    logging.info(f"Built and uploaded {file_key} for scan report {scan_report_id}")
    return file_key


def _drop_temp_rules_table(scan_report_id: int, table_suffix: str) -> None:
    try:
        pg_hook.run(
            "DROP TABLE IF EXISTS temp_rules_export_%(scan_report_id)s_%(suffix)s"
            % {"scan_report_id": int(scan_report_id), "suffix": table_suffix}
        )
    except Exception as e:
        logging.error(f"Could not drop temp rules table: {e}")


def full_validate(**kwargs) -> None:
    """Validate every row of the file; store the issues on the ImportJob."""
    params = pull_validated_params(kwargs, VALIDATE_PARAMS_TASK)
    plan = _build_plan(params, _job_file_key(params))
    pg_hook.run(
        queries.set_import_job_issues_query,
        parameters={
            "import_job_id": params["import_job_id"],
            "issues": json.dumps(plan.issues.as_dicts()),
        },
    )
    if not plan.ok:
        raise AirflowFailException(f"SSSOM file failed validation: {plan.summary()}")
    logging.info(f"SSSOM file is valid: {plan.summary()}")


def load(**kwargs) -> None:
    """Load the validated file into the registry tables, in one transaction."""
    params = pull_validated_params(kwargs, VALIDATE_PARAMS_TASK)
    file_key = _job_file_key(params)
    plan = _build_plan(params, file_key)
    try:
        with closing(pg_hook.get_conn()) as conn:
            load_plan(
                conn,
                plan,
                import_job_id=params["import_job_id"],
                origin=params["origin"],
                file_key=file_key,
                scan_report_id=params["scan_report_id"],
            )
    except LoadError as e:
        raise AirflowFailException(str(e))


def finalize(**kwargs) -> None:
    """Publish the set (unless a DRAFT was asked for) and mark the job SUCCEEDED."""
    params = pull_validated_params(kwargs, VALIDATE_PARAMS_TASK)
    import_job_id = params["import_job_id"]
    _, status = normalise_overrides(params["overrides"], IssueLog(0))
    with closing(pg_hook.get_conn()) as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    queries.publish_mapping_set_query,
                    {"status": status, "import_job_id": import_job_id},
                )
                row = cursor.fetchone()
                if not row:
                    raise AirflowFailException(
                        f"No mapping set was loaded for ImportJob {import_job_id}"
                    )
                cursor.execute(
                    queries.mark_import_job_succeeded_query,
                    {"import_job_id": import_job_id},
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    mapping_set_id, title = row
    done = "published to" if status == PUBLISHED else "saved as a draft in"
    create_import_job_notification(
        import_job_id,
        NotificationType.REGISTRY_IMPORT_COMPLETE,
        f"'{title}' was {done} the mappings registry",
        MAPPING_SET_URL.format(mapping_set_id=mapping_set_id),
    )


# ---------------------------------------------------------------------------
# Failure callback
# ---------------------------------------------------------------------------


def update_import_job_on_failure(context) -> None:
    """
    Mark the ImportJob FAILED, record why, and notify its submitter. Used as
    both the tasks' and the DAG's on_failure_callback: the task callback has the
    exception; the DAG callback also catches timeouts. Only the first records.
    """
    try:
        conf = context["dag_run"].conf or {}
        import_job_id = conf.get("import_job_id")
        if not import_job_id:
            logging.error("registry_import failed without an import_job_id in its conf")
            return
        exception = context.get("exception")
        task_instance = context.get("task_instance")
        if exception is not None:
            message = str(exception)
        elif context.get("reason"):
            message = str(context["reason"])
        else:
            task_id = getattr(task_instance, "task_id", "unknown")
            message = f"Task '{task_id}' was timed out or failed unexpectedly"

        with closing(pg_hook.get_conn()) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    queries.mark_import_job_failed_query,
                    {"import_job_id": import_job_id, "error_message": message},
                )
                updated = cursor.fetchone()
            conn.commit()

        if updated:
            create_import_job_notification(
                import_job_id,
                NotificationType.REGISTRY_IMPORT_FAILED,
                "Your mapping set import failed",
                IMPORT_JOB_URL.format(import_job_id=import_job_id),
            )

        # A failed direct publish may leave its temp rules table behind.
        scan_report_id = conf.get("scan_report_id")
        if conf.get("origin") == CARROT_DIRECT_PUBLISH and scan_report_id:
            try:
                suffix = temp_rules_table_suffix(import_job_id)
                scan_report_id = int(scan_report_id)
            except (TypeError, ValueError):
                # validate_params rejected these ids, so no table was created
                logging.info("Invalid ids in the run conf: no temp rules table to drop")
            else:
                _drop_temp_rules_table(scan_report_id, suffix)
    except Exception as e:
        logging.error(f"Failed to update ImportJob on failure: {e!s}")

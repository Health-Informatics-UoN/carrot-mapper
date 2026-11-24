"""
Step 3: validate every row of the job's SSSOM file, store the issues on the
ImportJob and, if there are no errors, load it into the registry tables.

The checks are in full_validate_and_load_checks.py (with the parser in
full_validate_and_load_parse.py) and the one-transaction load in
full_validate_and_load_db.py. Validating and loading in one step means the
file is read and checked once.
"""

from __future__ import annotations

import json
import logging
from contextlib import closing
from pathlib import Path
from typing import Any

from airflow.exceptions import AirflowFailException

from libs.db import pg_hook
from libs.registry_import import queries
from libs.registry_import.full_validate_and_load_checks import (
    CARROT_MAPPING_SET_NAMESPACE,
    ImportPlan,
    IssueLog,
    LicenseRow,
    SetRecord,
    Vocabulary,
    build_import,
    check_set_uri_not_reserved,
    check_set_version_is_newer,
    match_license,
    set_uri_uuid,
)
from libs.registry_import.full_validate_and_load_db import LoadError, load_plan
from libs.registry_import.full_validate_and_load_parse import decode, parse_sssom
from libs.registry_import.helpers import file_overrides, job_file_key
from libs.settings import REGISTRY_IMPORT_MAX_ISSUES, REGISTRY_SSSOM_CONTAINER
from libs.storage_services import download_blob_to_tmp
from libs.utils import pull_validated_params


def full_validate_and_load(**kwargs) -> None:
    params = pull_validated_params(kwargs, "validate_params_registry_import")
    import_job_id = params["import_job_id"]
    file_key = job_file_key(import_job_id)

    plan = _read_and_check(params, file_key)
    check_set_uri_not_reserved(plan, params["origin"], _local_scan_report_id(plan))
    check_set_version_is_newer(plan, _existing_versions(plan, import_job_id))
    pg_hook.run(
        queries.set_import_job_issues_query,
        parameters={
            "import_job_id": import_job_id,
            "issues": json.dumps(plan.issues.as_dicts()),
        },
    )
    if not plan.ok:
        raise AirflowFailException(f"SSSOM file failed validation: {plan.summary()}")
    logging.info(f"SSSOM file is valid: {plan.summary()}")

    try:
        with closing(pg_hook.get_conn()) as conn:
            load_plan(
                conn,
                plan,
                import_job_id=import_job_id,
                origin=params["origin"],
                file_key=file_key,
                scan_report_id=params["scan_report_id"],
            )
    except LoadError as e:
        raise AirflowFailException(str(e))


def _read_and_check(params: dict[str, Any], file_key: str) -> ImportPlan:
    """
    Download the job's SSSOM file and parse, check and normalise all of it into
    the rows load_plan inserts.
    """
    vocab = Vocabulary(
        predicates={r[0] for r in pg_hook.get_records(queries.get_predicates_query)},
        justifications={
            r[0] for r in pg_hook.get_records(queries.get_justifications_query)
        },
        prefixes=dict(pg_hook.get_records(queries.get_prefixes_query)),
    )

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
    file_iri = parsed.metadata.get("license")
    return build_import(
        parsed,
        vocab,
        file_overrides(params),
        # the License id validate_params checked (None if the request had none)
        license_id=params["overrides"].get("license") or None,
        max_issues=REGISTRY_IMPORT_MAX_ISSUES,
        # the set a request adds a version to (validate_params checked it)
        series_set_uri=params.get("series_set_uri"),
        # the License the file's license IRI stands for, compared to the request's
        file_license_id=(
            match_license(str(file_iri), _licenses())
            if file_iri not in (None, "")
            else None
        ),
    )


def _licenses() -> list[LicenseRow]:
    """The registry's Licenses (a few hundred, from the SPDX License List)."""
    return [
        LicenseRow(id, iri, tuple(see_also or ()), is_deprecated)
        for id, iri, see_also, is_deprecated in pg_hook.get_records(
            queries.get_license_iris_query
        )
    ]


def _existing_versions(plan: ImportPlan, import_job_id: str) -> list[str]:
    """Versions of this file's set_uri from other imports."""
    record = plan.mapping_set
    if not record.set_uri:
        return []
    rows = pg_hook.get_records(
        queries.get_set_versions_query,
        parameters={"set_uri": record.set_uri, "import_job_id": import_job_id},
    )
    return [row[0] for row in rows]


def _local_scan_report_id(plan: ImportPlan) -> int | None:
    """
    The scan report on this instance whose set id the file uses, if any. Only
    Carrot set ids ({namespace}{ScanReport.uuid}) are looked up: another
    namespace's id may end in a UUID too.
    """
    set_uri = plan.mapping_set.set_uri
    if not set_uri.startswith(CARROT_MAPPING_SET_NAMESPACE):
        return None
    scan_report_uuid = set_uri_uuid(set_uri)
    if scan_report_uuid is None:
        return None
    row = pg_hook.get_first(
        queries.get_scan_report_by_uuid_query,
        parameters={"uuid": scan_report_uuid},
    )
    return row[0] if row else None

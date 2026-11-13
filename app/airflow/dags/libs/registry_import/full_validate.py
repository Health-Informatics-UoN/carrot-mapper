"""
Step 3: validate every row of the job's SSSOM file and store the issues on the
ImportJob. The checks themselves are in full_validate_checks.py.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from airflow.exceptions import AirflowFailException

from libs.db import pg_hook
from libs.registry_import import queries
from libs.registry_import.full_validate_checks import (
    ImportPlan,
    IssueLog,
    SetRecord,
    Vocabulary,
    build_import,
)
from libs.registry_import.full_validate_licenses import License, LicenseLookup
from libs.registry_import.full_validate_parse import decode, parse_sssom
from libs.registry_import.helpers import (
    file_overrides,
    job_file_key,
)
from libs.settings import REGISTRY_IMPORT_MAX_ISSUES, REGISTRY_SSSOM_CONTAINER
from libs.storage_services import download_blob_to_tmp
from libs.utils import pull_validated_params


def full_validate(**kwargs) -> None:
    params = pull_validated_params(kwargs, "validate_params_registry_import")
    plan = read_import_plan(params, job_file_key(params["import_job_id"]))
    _check_set_version_is_new(plan, params["import_job_id"])
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


def read_import_plan(params: dict[str, Any], file_key: str) -> ImportPlan:
    """
    Download the job's SSSOM file and parse, check and normalise all of it into
    the rows load inserts.

    Both full_validate and load call this. Steps pass each other only ids
    through XCom, never data, and may run on different workers, so load
    re-reads the stored file rather than receiving the rows. It's
    deterministic, so load gets exactly what full_validate accepted (load
    refuses a plan with errors in any case).
    """
    vocab = Vocabulary(
        predicates={r[0] for r in pg_hook.get_records(queries.get_predicates_query)},
        justifications={
            r[0] for r in pg_hook.get_records(queries.get_justifications_query)
        },
    )
    licenses = LicenseLookup(
        License(license_id, license_iri, tuple(see_also or ()), is_deprecated)
        for license_id, license_iri, see_also, is_deprecated in pg_hook.get_records(
            queries.get_licenses_query
        )
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
    return build_import(
        parsed,
        vocab,
        licenses,
        file_overrides(params),
        max_issues=REGISTRY_IMPORT_MAX_ISSUES,
    )


def _check_set_version_is_new(plan: ImportPlan, import_job_id: str) -> None:
    """Sets are immutable: another import mustn't hold this set_uri + version."""
    record = plan.mapping_set
    if not (record.set_uri and record.set_version):
        return
    conflict = pg_hook.get_first(
        queries.get_conflicting_set_query,
        parameters={
            "set_uri": record.set_uri,
            "set_version": record.set_version,
            "import_job_id": import_job_id,
        },
    )
    if conflict:
        plan.issues.error(
            "set_version_exists",
            f"Mapping set {record.set_uri} version {record.set_version} already "
            "exists; publish corrections as a new mapping_set_version",
            column="mapping_set_version",
        )

"""
Step 2: make sure the job's SSSOM file is in storage.

- SSSOM_UPLOAD: nothing to do. The API's upload endpoint stored the file (at
  helpers.file_key_for(job id)) and set ImportJob.file_key before triggering.
- CARROT_DIRECT_PUBLISH: build the file from the scan report's mappings with
  the rules SSSOM exporter, adding the set identity from the overrides, and
  store it.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from airflow.exceptions import AirflowFailException

from libs.db import pg_hook
from libs.queries import create_update_temp_rules_table_query
from libs.registry_import import queries
from libs.registry_import.full_validate_checks import (
    OVERRIDE_SLOTS,
    IssueLog,
    normalise_overrides,
)
from libs.registry_import.helpers import (
    CARROT_DIRECT_PUBLISH,
    SSSOM_UPLOAD,
    VALIDATE_PARAMS_TASK,
    drop_temp_rules_table,
    file_key_for,
    file_overrides,
    job_file_key,
    temp_rules_table_suffix,
)
from libs.rules_export.file_services import fetch_sssom_rules, get_creator
from libs.rules_export.sssom import write_sssom_tsv
from libs.settings import AIRFLOW_DEBUG_MODE, REGISTRY_SSSOM_CONTAINER
from libs.storage_services import upload_blob_to_storage
from libs.utils import pull_validated_params


def prepare_source(**kwargs) -> str:
    """Returns the job's file_key."""
    params = pull_validated_params(kwargs, VALIDATE_PARAMS_TASK)
    origin = params["origin"]
    if origin == SSSOM_UPLOAD:
        file_key = job_file_key(params["import_job_id"])
        logging.info(f"SSSOM upload: using stored file {file_key}")
        return file_key
    if origin == CARROT_DIRECT_PUBLISH:
        return build_direct_publish_file(params)
    # An origin seeded in registry_origin that this DAG doesn't handle yet
    raise AirflowFailException(
        f"registry_import can't prepare a file for origin {origin}"
    )


def build_direct_publish_file(params: dict[str, Any]) -> str:
    """Write the scan report's mappings as SSSOM and store them; returns the key."""
    import_job_id = params["import_job_id"]
    scan_report_id = params["scan_report_id"]
    slots, _ = normalise_overrides(file_overrides(params), IssueLog(0))

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
        if not params["overrides"]["include_orcid_ids"]:
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
            drop_temp_rules_table(scan_report_id, table_suffix)

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

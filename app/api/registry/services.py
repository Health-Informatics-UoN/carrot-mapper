import logging
from typing import Any

from activity_log.models import ScopeType, Verb
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from mapping.models import MappingRule, ScanReport
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from services.activity_log import record as record_activity
from services.worker_service import get_worker_service

from registry.models import (
    CARROT_MAPPING_SET_NAMESPACE,
    ImportJob,
    ImportJobStatus,
    MappingSet,
    Origin,
)
from registry.versions import NotSemVer, ReleaseType, bump, latest_semver

logger = logging.getLogger(__name__)

worker_service = get_worker_service()


class PublishConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"


class WorkerUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "The registry import could not be started, please try again later."
    default_code = "worker_unavailable"


def scan_report_set_uri(scan_report: ScanReport) -> str:
    return f"{CARROT_MAPPING_SET_NAMESPACE}scanreport/{scan_report.pk}"


def scan_report_has_publishable_mappings(scan_report: ScanReport) -> bool:
    """Only *_concept_id rules become SSSOM rows (see airflow rules_export/sssom.py)."""
    return MappingRule.objects.filter(
        scan_report=scan_report, omop_field__field__endswith="_concept_id"
    ).exists()


def latest_set_version(scan_report: ScanReport) -> str | None:
    """
    The highest version of the scan report's mapping set, any status (a
    withdrawn or draft version still holds its number). Raises
    PublishConflict if a version isn't SemVer, as the next one can't be derived.
    """
    versions = MappingSet.objects.filter(
        set_uri=scan_report_set_uri(scan_report)
    ).values_list("set_version", flat=True)
    try:
        return latest_semver(versions)
    except NotSemVer as e:
        logger.exception("Non-SemVer mapping set version encountered while deriving next version.")
        raise PublishConflict(
            {
                "detail": "This mapping set has a non-SemVer version, so the next version can't be derived."
            }
        ) from e


def next_versions(scan_report: ScanReport) -> dict[str, Any]:
    """The latest version and the version each release type would publish."""
    latest = latest_set_version(scan_report)
    return {
        "latest_version": latest,
        "next_versions": {
            release_type: bump(latest, release_type)
            for release_type in ReleaseType.values
        },
    }


def submit_direct_publish(
    scan_report: ScanReport,
    user: User,
    metadata: dict[str, Any],
    mapper_version: str,
) -> tuple[ImportJob, bool]:
    """
    Queue a scan report's mappings for import into the registry.

    The version is the next SemVer of ``metadata["release_type"]`` after the
    set's highest version (1.0.0 for the first publish).

    Creates a PENDING ImportJob and triggers the registry import DAG, which
    builds the SSSOM file from the scan report and loads it. Returns
    ``(job, created)``; ``created`` is False when an identical publish is
    already in flight and that job is returned instead.

    Raises ValidationError (400) if there is nothing to publish,
    PublishConflict (409) if an existing version isn't SemVer or a different
    publish of the scan report is in flight, and WorkerUnavailable (503) if
    the DAG cannot be triggered (the job is then marked FAILED).
    """
    set_uri = scan_report_set_uri(scan_report)

    with transaction.atomic():
        # Serialises concurrent publishes of the same scan report, so two
        # requests can't both pass the checks below.
        ScanReport.objects.select_for_update().filter(pk=scan_report.pk).first()

        if not scan_report_has_publishable_mappings(scan_report):
            raise ValidationError(
                {"detail": "This scan report has no concept mappings to publish."}
            )

        set_version = bump(latest_set_version(scan_report), metadata["release_type"])
        overrides = {
            "set_uri": set_uri,
            "set_version": set_version,
            "title": metadata["title"],
            "description": metadata.get("description", ""),
            "license": metadata["license"].pk,
            "status": metadata["status"],
            "include_author_orcid_ids": metadata.get("include_author_orcid_ids", False),
        }

        # One publish per scan report at a time: the next version is derived
        # from the loaded ones, so a second publish would get the same number.
        in_flight = ImportJob.objects.filter(
            origin_id=Origin.CARROT_DIRECT_PUBLISH,
            status__in=[ImportJobStatus.PENDING, ImportJobStatus.RUNNING],
            params__scan_report_id=scan_report.pk,
        ).first()
        if in_flight:
            if in_flight.params.get("overrides") == overrides:
                return in_flight, False
            in_flight_version = in_flight.params.get("overrides", {}).get("set_version")
            raise PublishConflict(
                {
                    "detail": f"Version '{in_flight_version}' of this mapping set "
                    "is already being published. Try again once it has finished.",
                    "import_job_id": str(in_flight.id),
                }
            )

        params = {
            "origin": Origin.CARROT_DIRECT_PUBLISH,
            "scan_report_id": scan_report.pk,
            "user_id": user.pk,
            # recorded as mapping_tool_version in the generated SSSOM file
            "mapper_version": mapper_version,
            "overrides": overrides,
        }
        job = ImportJob.objects.create(
            submitted_by=user,
            origin_id=Origin.CARROT_DIRECT_PUBLISH,
            params=params,
        )

    # Triggered after commit so the DAG can always see the job row.
    try:
        dag_run_id = worker_service.trigger_registry_import(
            {"import_job_id": str(job.id), **params}
        )
    except Exception as e:
        logger.exception("Failed to trigger registry import for job %s", job.id)
        job.status = ImportJobStatus.FAILED
        job.error_message = f"Failed to trigger the registry import: {e}"
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_message", "finished_at"])
        raise WorkerUnavailable() from e

    # update_fields so a DAG that has already set the job RUNNING isn't overwritten.
    job.dag_run_id = dag_run_id or ""
    job.save(update_fields=["dag_run_id"])

    record_activity(
        scope_type=ScopeType.SCAN_REPORT,
        scope_id=scan_report.pk,
        verb=Verb.REGISTRY_PUBLISH_REQUESTED,
        actor=user,
        object_type="registryimportjob",
        detail={"title": overrides["title"], "set_version": set_version},
    )

    return job, True

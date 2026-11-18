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
    Status,
)

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
    return f"{CARROT_MAPPING_SET_NAMESPACE}{scan_report.uuid}"


def scan_report_has_publishable_mappings(scan_report: ScanReport) -> bool:
    """Only *_concept_id rules become SSSOM rows (see airflow rules_export/sssom.py)."""
    return MappingRule.objects.filter(
        scan_report=scan_report, omop_field__field__endswith="_concept_id"
    ).exists()


def submit_direct_publish(
    scan_report: ScanReport,
    user: User,
    metadata: dict[str, Any],
    mapper_version: str,
) -> tuple[ImportJob, bool]:
    """
    Queue a scan report's mappings for import into the registry.

    Creates a PENDING ImportJob and triggers the registry import DAG, which
    builds the SSSOM file from the scan report and loads it. Returns
    ``(job, created)``; ``created`` is False when an identical publish is
    already in flight and that job is returned instead.

    Raises ValidationError (400) if there is nothing to publish,
    PublishConflict (409) if the version is taken or a different publish of
    it is in flight, and WorkerUnavailable (503) if the DAG cannot be
    triggered (the job is then marked FAILED).
    """
    set_uri = scan_report_set_uri(scan_report)
    set_version = metadata["set_version"]
    overrides = {
        "set_uri": set_uri,
        "set_version": set_version,
        "title": metadata["title"],
        "description": metadata.get("description", ""),
        "license": metadata["license"].pk,
        "status": metadata["status"],
        "include_author_orcid_ids": metadata.get("include_author_orcid_ids", False),
    }

    with transaction.atomic():
        # Serialises concurrent publishes of the same scan report, so two
        # requests can't both pass the checks below.
        ScanReport.objects.select_for_update().filter(pk=scan_report.pk).first()

        if not scan_report_has_publishable_mappings(scan_report):
            raise ValidationError(
                {"detail": "This scan report has no concept mappings to publish."}
            )

        # The first version of a set_uri decides who may add versions to it
        # (the registry_import DAG checks this again when it loads the file).
        first_version = (
            MappingSet.objects.filter(set_uri=set_uri).order_by("created_at").first()
        )
        if (
            first_version is not None
            and first_version.source_scan_report_id != scan_report.pk
        ):
            raise PublishConflict(
                {
                    "detail": "This mapping set's identifier is already used by "
                    "a mapping set that was not published from this scan report."
                }
            )

        if MappingSet.objects.filter(set_uri=set_uri, set_version=set_version).exists():
            raise PublishConflict(
                {
                    "detail": f"Version '{set_version}' of this mapping set "
                    "already exists. Publish a new version instead."
                }
            )

        in_flight = ImportJob.objects.filter(
            origin_id=Origin.CARROT_DIRECT_PUBLISH,
            status__in=[ImportJobStatus.PENDING, ImportJobStatus.RUNNING],
            params__scan_report_id=scan_report.pk,
            params__overrides__set_version=set_version,
        ).first()
        if in_flight:
            if in_flight.params.get("overrides") == overrides:
                return in_flight, False
            raise PublishConflict(
                {
                    "detail": f"Version '{set_version}' of this mapping set "
                    "is already being published.",
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
        job.error_message = WorkerUnavailable.default_detail
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


def _lock_finished_mapping_set(mapping_set_id) -> MappingSet:
    """
    Lock a set whose import has finished, for a status change. Call in a
    transaction.

    The registry_import DAG writes the set's status while the job runs, so a
    set is only ours to change once the job has SUCCEEDED. finalize updates the
    set and the job in one transaction, so the job is read after taking the
    lock, to see the result of a finalize that held it.
    """
    mapping_set = MappingSet.objects.select_for_update().get(pk=mapping_set_id)
    if mapping_set.import_job_id:
        job_status = (
            ImportJob.objects.filter(pk=mapping_set.import_job_id)
            .values_list("status", flat=True)
            .first()
        )
        if job_status != ImportJobStatus.SUCCEEDED:
            raise PublishConflict(
                {"detail": "This mapping set's import has not finished."}
            )
    return mapping_set


def publish_mapping_set(mapping_set_id, user: User) -> None:
    """DRAFT -> PUBLISHED. Raises PublishConflict (409) from any other state."""
    with transaction.atomic():
        mapping_set = _lock_finished_mapping_set(mapping_set_id)
        if mapping_set.status_id != Status.DRAFT:
            raise PublishConflict(
                {"detail": "Only a draft mapping set can be published."}
            )
        mapping_set.status_id = Status.PUBLISHED
        mapping_set.published_at = timezone.now()
        mapping_set.save(update_fields=["status", "published_at"])
    logger.info("User %s published mapping set %s", user.pk, mapping_set_id)


def withdraw_mapping_set(mapping_set_id, user: User, reason: str) -> None:
    """
    PUBLISHED -> WITHDRAWN. The set stays resolvable by id but leaves search.
    Raises PublishConflict (409) from any other state.
    """
    with transaction.atomic():
        mapping_set = _lock_finished_mapping_set(mapping_set_id)
        if mapping_set.status_id != Status.PUBLISHED:
            raise PublishConflict(
                {"detail": "Only a published mapping set can be withdrawn."}
            )
        mapping_set.status_id = Status.WITHDRAWN
        mapping_set.withdrawn_at = timezone.now()
        mapping_set.withdrawn_by = user
        mapping_set.withdrawal_reason = reason
        mapping_set.save(
            update_fields=[
                "status",
                "withdrawn_at",
                "withdrawn_by",
                "withdrawal_reason",
            ]
        )
    logger.info("User %s withdrew mapping set %s", user.pk, mapping_set_id)

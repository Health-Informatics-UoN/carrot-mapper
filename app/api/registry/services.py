import io
import logging
import uuid
from typing import Any

from activity_log.models import ScopeType, Verb
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.db import connection, transaction
from django.utils import timezone
from mapping.models import MappingRule, ScanReport
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from services.activity_log import record as record_activity
from services.storage_service import StorageService
from services.worker_service import get_worker_service

from registry.models import (
    CARROT_MAPPING_SET_NAMESPACE,
    ImportJob,
    ImportJobStatus,
    MappingSet,
    Origin,
    Status,
)
from registry.validation import (
    ValidationReport,
    check_set_identity,
    in_flight_import,
    validate_upload,
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


class UploadRejected(Exception):
    """An uploaded file was refused; ``report`` says why."""

    def __init__(self, report: ValidationReport, status_code: int):
        super().__init__("SSSOM upload rejected")
        self.report = report
        self.status_code = status_code


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
    _trigger_import(job, {"import_job_id": str(job.id), **params})

    record_activity(
        scope_type=ScopeType.SCAN_REPORT,
        scope_id=scan_report.pk,
        verb=Verb.REGISTRY_PUBLISH_REQUESTED,
        actor=user,
        object_type="registryimportjob",
        detail={"title": overrides["title"], "set_version": set_version},
    )

    return job, True


def _fail_unstarted_job(job: ImportJob) -> None:
    job.status = ImportJobStatus.FAILED
    job.error_message = WorkerUnavailable.default_detail
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "error_message", "finished_at"])


def _trigger_import(job: ImportJob, conf: dict[str, Any]) -> None:
    """Start the DAG, or mark the job FAILED and raise WorkerUnavailable (503)."""
    try:
        dag_run_id = worker_service.trigger_registry_import(conf)
    except Exception as e:
        logger.exception("Failed to trigger registry import for job %s", job.id)
        _fail_unstarted_job(job)
        raise WorkerUnavailable() from e

    # update_fields so a DAG that has already set the job RUNNING isn't overwritten.
    job.dag_run_id = dag_run_id or ""
    job.save(update_fields=["dag_run_id"])


def _is_same_upload(job: ImportJob, report: ValidationReport, user, status) -> bool:
    return (
        job.submitted_by_id == user.pk
        and job.params.get("sha256") == report.sha256
        and job.params.get("overrides", {}).get("status") == status
    )


def _lock_set_identity(set_uri: str) -> None:
    """
    Serialise submissions of one set_uri until the transaction ends, so two
    requests can't both pass the checks. The key differs from the DAG's load
    lock: a request must not wait for a long-running load.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            [f"registry-submit:{set_uri}"],
        )


def _add_in_flight_conflict(report: ValidationReport, job: ImportJob) -> None:
    report.error(
        "version_in_flight",
        f"Version {report.set_version!r} of this mapping set is already being "
        f"imported (job {job.id})",
        column="mapping_set_version",
    )


def dry_run_upload(upload: UploadedFile, user: User) -> ValidationReport:
    """Every check POST imports/ makes, without storing or starting anything."""
    report = validate_upload(upload)
    if report.has_content_errors or not report.set_uri or not report.set_version:
        return report
    in_flight = in_flight_import(report.set_uri, report.set_version)
    if in_flight is None:
        check_set_identity(report, user)
    elif (
        in_flight.submitted_by_id == user.pk
        and in_flight.params.get("sha256") == report.sha256
    ):
        report.warning(
            "import_in_progress",
            f"This file is already being imported (job {in_flight.id})",
        )
    else:
        _add_in_flight_conflict(report, in_flight)
    return report


def submit_upload(
    upload: UploadedFile,
    user: User,
    requested_status: str,
    idempotency_key: str = "",
) -> tuple[ImportJob, ValidationReport, bool]:
    """
    Quick-validate an SSSOM file, store it and queue its import.

    Returns ``(job, report, created)``; ``created`` is False when this is a
    repeat of an import already under way, whose job is returned instead.

    Raises UploadRejected (400 for a bad file, 409 when the set version can't
    be taken) and WorkerUnavailable (503) if the file can't be stored or the DAG
    can't be triggered (the job is then marked FAILED).
    """
    report = validate_upload(upload)

    if idempotency_key and report.sha256:
        earlier = (
            ImportJob.objects.filter(
                submitted_by=user, params__idempotency_key=idempotency_key
            )
            .exclude(status=ImportJobStatus.FAILED)
            .first()
        )
        if earlier is not None:
            if earlier.params.get("sha256") == report.sha256:
                return earlier, report, False
            report.error(
                "idempotency_key_reused",
                "This Idempotency-Key was already used for a different file",
            )
            raise UploadRejected(report, status.HTTP_409_CONFLICT)

    if not report.valid:
        raise UploadRejected(report, status.HTTP_400_BAD_REQUEST)

    job_id = uuid.uuid4()
    file_key = f"imports/{job_id}/original.sssom.tsv"
    # The License is worked out from the file's own license IRI: the DAG can
    # only link a set to a License named in its run conf.
    overrides: dict[str, Any] = {"status": requested_status}
    if report.license_id:
        overrides["license"] = report.license_id
    conf = {
        "origin": Origin.SSSOM_UPLOAD,
        "user_id": user.pk,
        "file_key": file_key,
        "overrides": overrides,
    }

    with transaction.atomic():
        _lock_set_identity(report.set_uri)
        in_flight = in_flight_import(report.set_uri, report.set_version)
        if in_flight is not None:
            if _is_same_upload(in_flight, report, user, requested_status):
                return in_flight, report, False
            _add_in_flight_conflict(report, in_flight)
            raise UploadRejected(report, status.HTTP_409_CONFLICT)
        check_set_identity(report, user)
        if not report.valid:
            raise UploadRejected(report, status.HTTP_409_CONFLICT)
        job = ImportJob.objects.create(
            id=job_id,
            submitted_by=user,
            origin_id=Origin.SSSOM_UPLOAD,
            file_key=file_key,
            params={
                **conf,
                "sha256": report.sha256,
                "set_uri": report.set_uri,
                "set_version": report.set_version,
                "idempotency_key": idempotency_key,
            },
        )

    # After commit: no transaction is held open across the network.
    try:
        StorageService().upload_file(
            file_key,
            settings.REGISTRY_SSSOM_CONTAINER,
            io.BytesIO(report.data),
            "text/tab-separated-values",
            use_read_method=True,
        )
    except Exception as e:
        logger.exception("Failed to store the SSSOM file of import job %s", job.id)
        _fail_unstarted_job(job)
        raise WorkerUnavailable() from e

    _trigger_import(job, {"import_job_id": str(job.id), **conf})
    logger.info("User %s submitted SSSOM import job %s", user.pk, job.id)
    return job, report, True


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

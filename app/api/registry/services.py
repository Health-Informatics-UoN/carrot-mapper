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
    MappingSetSeries,
    Origin,
)
from registry.validation import (
    ValidationReport,
    check_set_identity,
    in_flight_import,
    validate_upload,
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


def latest_set_version(scan_report: ScanReport) -> str | None:
    """
    The highest version of the scan report's mapping set, any status (a
    withdrawn or draft version still holds its number). Raises
    PublishConflict if a version isn't SemVer, as the next one can't be derived.
    """
    versions = MappingSet.objects.filter(
        series__set_uri=scan_report_set_uri(scan_report)
    ).values_list("set_version", flat=True)
    try:
        return latest_semver(versions)
    except NotSemVer as e:
        logger.exception(
            "Non-SemVer mapping set version encountered while deriving next version."
        )
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
        # The set's owner decides who may add versions to it (the
        # registry_import DAG checks this again when it loads the file).
        # Checked before deriving the version: another publisher's set may
        # use non-SemVer versions, which would otherwise mask this conflict.
        series = MappingSetSeries.objects.filter(set_uri=set_uri).first()
        if series is not None and series.source_scan_report_id != scan_report.pk:
            raise PublishConflict(
                {
                    "detail": "This mapping set's identifier is already used by "
                    "a mapping set that was not published from this scan report."
                }
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
        if MappingSet.objects.filter(
            series__set_uri=set_uri, set_version=set_version
        ).exists():
            raise PublishConflict(
                {
                    "detail": f"Version '{set_version}' of this mapping set "
                    "already exists. Publish a new version instead."
                }
            )

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


def _in_flight_upload_of(report: ValidationReport, user) -> ImportJob | None:
    """The user's unfinished upload of this exact file, if any."""
    return (
        ImportJob.objects.filter(
            submitted_by=user,
            origin_id=Origin.SSSOM_UPLOAD,
            params__sha256=report.sha256,
            status__in=[ImportJobStatus.PENDING, ImportJobStatus.RUNNING],
        )
        .order_by("created_at")
        .first()
    )


def dry_run_upload(upload: UploadedFile, user: User) -> ValidationReport:
    """Every check POST imports/ makes, without storing or starting anything."""
    report = validate_upload(upload)
    if report.has_content_errors or not report.set_version:
        return report
    if not report.set_uri:
        in_flight = _in_flight_upload_of(report, user)
        if in_flight is not None:
            report.warning(
                "import_in_progress",
                f"This file is already being imported (job {in_flight.id})",
            )
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
    # Only the status: the DAG takes everything else, the License included,
    # from the file, which must agree with any request override.
    overrides: dict[str, Any] = {"status": requested_status}
    conf = {
        "origin": Origin.SSSOM_UPLOAD,
        "user_id": user.pk,
        "file_key": file_key,
        "overrides": overrides,
    }

    with transaction.atomic():
        if report.set_uri:
            _lock_set_identity(report.set_uri)
            in_flight = in_flight_import(report.set_uri, report.set_version)
        else:
            # Without a mapping_set_id each upload is a new set, so only a
            # repeat of this file is the same import.
            _lock_set_identity(f"file:{user.pk}:{report.sha256}")
            in_flight = _in_flight_upload_of(report, user)
        if in_flight is not None:
            if _is_same_upload(in_flight, report, user, requested_status):
                return in_flight, report, False
            if report.set_uri:
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

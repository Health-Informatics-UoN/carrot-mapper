import json
import os
from datetime import timedelta

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from jobs.models import Job, JobStage, StageStatus
from mapping.models import ScanReport
from rest_framework.filters import OrderingFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import DestroyModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from services.storage_service import StorageService
from services.worker_service import get_worker_service

from files.paginations import CustomPagination

from .models import FileDownload
from .serializers import FileDownloadSerializer

storage_service = StorageService()
worker_service = get_worker_service()


class FileDownloadView(
    GenericAPIView, ListModelMixin, RetrieveModelMixin, DestroyModelMixin
):
    """
    A view for handling file downloads and file generation requests.
    This view provides functionality to:
    - Retrieve a list of downloadable files associated with a specific scan report.
    - Download a specific file by its primary key.
    - Request the generation of a file for download by sending a message to a queue.
    - Delete a file manually from storage and database.
    - Automatically filter files older than FILE_RETENTION_DAYS from the list.
    Attributes:
        serializer_class (Serializer): The serializer class used for file downloads.
        filter_backends (list): The list of filter backends for filtering querysets.
        pagination_class (Pagination): The pagination class for paginating results.
        permission_classes (list): The list of permission classes for access control.
        ordering (str): The default ordering for querysets.
    Methods:
        get_queryset():
            Retrieves the queryset of FileDownload objects filtered by the scan report ID
            and age (files older than FILE_RETENTION_DAYS are excluded).
        get(request, *args, **kwargs):
            Handles GET requests. If a primary key is provided, it downloads the file.
            Otherwise, it returns a paginated list of files.
        post(request, *args, **kwargs):
            Handles POST requests to request the generation of a file for download.
        delete(request, *args, **kwargs):
            Handles DELETE requests to manually remove a file from storage and database.
    """

    serializer_class = FileDownloadSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    pagination_class = CustomPagination
    permission_classes = [IsAuthenticated]
    ordering = "-created_at"

    @extend_schema(responses=FileDownloadSerializer)
    def get_queryset(self):
        scan_report_id = self.kwargs["scanreport_pk"]
        scan_report = get_object_or_404(ScanReport, pk=scan_report_id)

        # Hide files older than retention period (default: 30 days)
        retention_days = int(os.getenv("FILE_RETENTION_DAYS", "30"))
        cutoff_date = timezone.now() - timedelta(days=retention_days)

        # Only show recent, non-deleted files
        return FileDownload.objects.filter(
            scan_report=scan_report,
            created_at__gte=cutoff_date,
            deleted_at__isnull=True,
        )

    def get(self, request, *args, **kwargs):
        if "pk" in kwargs:
            entity = get_object_or_404(FileDownload, pk=kwargs["pk"])
            file = storage_service.get_file(entity.file_url, "rules-exports")

            response = HttpResponse(file, content_type="application/octet-stream")
            response["Content-Disposition"] = f'attachment; filename="{entity.name}"'
            return response

        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to initiate the generation of a downloadable
        file by sending a message to the Rules Export Queue and creating a
        corresponding job record.

        This endpoint expects a JSON payload containing the following fields:
            - scan_report_id (int): The ID of the scan report for which the
            file is to be generated.
            - file_type (str): The type of file to generate (e.g.,
            'application/json_v1', 'application/json_v2', or 'text/csv').

        Upon successful validation of the input, a message is sent to the
        Rules Export Queue, and a job record is created in the database to
        track the file generation process.

        Returns:
            - 202 Accepted: If the request is successfully processed and
            the file generation is initiated.
            - 400 Bad Request: If the required fields ('scan_report_id' or
            'file_type') are missing or if the JSON payload is invalid.
            - 500 Internal Server Error: If an unexpected error occurs
            during processing.

        Raises:
            - json.JSONDecodeError: If the request body contains invalid
            JSON.
            - Exception: For any other unexpected errors.

        Note:
            - A job record is created with the status set to "IN_PROGRESS"
            and includes details about the file type being generated.
        """
        try:
            body = request.data
            scan_report_id = body.get("scan_report_id")
            file_type = body.get("file_type")

            if not scan_report_id or not file_type:
                return JsonResponse(
                    {"error": "scan_report_id and file_type are required."}, status=400
                )
            # Get the scan report model to get the scan report name for both Azure and Airflow tasks later on
            scan_report = ScanReport.objects.get(id=scan_report_id)

            # Determine the JSON version for the message
            json_version = "v1"  # default
            if file_type == "application/json_v2":
                json_version = "v2"
            elif file_type == "application/json_v1":
                json_version = "v1"

            msg = {
                "scan_report_id": scan_report_id,
                "scan_report_name": scan_report.dataset,
                "user_id": request.user.id,
                "file_type": file_type,
                "json_version": json_version,
            }

            worker_service.trigger_rules_export(msg)

            # Create job record for downloading file
            file_type_description = (
                "JSON V1"
                if file_type == "application/json_v1"
                else "JSON V2" if file_type == "application/json_v2" else "CSV"
            )
            Job.objects.create(
                scan_report=ScanReport.objects.get(id=scan_report_id),
                stage=JobStage.objects.get(value="DOWNLOAD_RULES"),
                status=StageStatus.objects.get(value="IN_PROGRESS"),
                details=f"A Mapping Rules {file_type_description} is being generated.",
            )
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data."}, status=400)
        except Exception:
            return JsonResponse({"error": "Internal server error."}, status=500)

        return HttpResponse(status=202)

    def delete(self, request, *args, **kwargs):
        """
        Handles DELETE requests to soft-delete a file from storage.

        This allows users to immediately delete unwanted files before the automatic
        retention period expires. The physical file is removed from storage (Azure/MinIO)
        but the database record is kept for audit purposes with a deleted_at timestamp.

        Args:
            request: The HTTP request object.
            *args: Variable length argument list.
            **kwargs: Must contain 'pk' - the primary key of the FileDownload to delete.

        Returns:
            - 204 No Content: If the file is successfully deleted.
            - 404 Not Found: If the file doesn't exist.
            - 500 Internal Server Error: If an error occurs during deletion.
        """
        try:
            file_download = get_object_or_404(FileDownload, pk=kwargs["pk"])

            # Delete the physical file from storage if file_url exists
            if file_download.file_url:
                try:
                    storage_service.delete_file(file_download.file_url, "rules-exports")
                except Exception:
                    pass  # File may not exist in storage

            # Mark as deleted but keep record for audit
            file_download.deleted_at = timezone.now()
            file_download.save()

            return HttpResponse(status=204)
        except Exception:
            return JsonResponse({"error": "Internal server error."}, status=500)

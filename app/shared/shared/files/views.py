import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from shared.files.paginations import CustomPagination
from shared.jobs.models import Job, JobStage, StageStatus
from shared.mapping.models import ScanReport
from drf_spectacular.utils import extend_schema
from shared.services.storage_service import StorageService
from shared.services.worker_service import get_worker_service

from .models import FileDownload
from .serializers import FileDownloadSerializer

storage_service = StorageService()
worker_service = get_worker_service()


class FileDownloadView(GenericAPIView, ListModelMixin, RetrieveModelMixin):
    """
    A view for handling file downloads and file generation requests.
    This view provides functionality to:
    - Retrieve a list of downloadable files associated with a specific scan report.
    - Download a specific file by its primary key.
    - Request the generation of a file for download by sending a message to a queue.
    Attributes:
        serializer_class (Serializer): The serializer class used for file downloads.
        filter_backends (list): The list of filter backends for filtering querysets.
        pagination_class (Pagination): The pagination class for paginating results.
        permission_classes (list): The list of permission classes for access control.
        ordering (str): The default ordering for querysets.
    Methods:
        get_queryset():
            Retrieves the queryset of FileDownload objects filtered by the scan report ID.
        get(request, *args, **kwargs):
            Handles GET requests. If a primary key is provided, it downloads the file.
            Otherwise, it returns a paginated list of files.
        post(request, *args, **kwargs):
            Handles POST requests to request the generation of a file for download.
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

        return FileDownload.objects.filter(scan_report=scan_report)

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
            'application/json' or 'text/csv').

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
            - The `add_message` function is used to send the message to the
            Rules Export Queue.
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
            msg = {
                "scan_report_id": scan_report_id,
                "scan_report_name": scan_report.dataset,
                "user_id": request.user.id,
                "file_type": file_type,
            }

            worker_service.trigger_rules_export(msg)
            # Create job record for downloading file
            Job.objects.create(
                scan_report=ScanReport.objects.get(id=scan_report_id),
                stage=JobStage.objects.get(value="DOWNLOAD_RULES"),
                status=StageStatus.objects.get(value="IN_PROGRESS"),
                details=f"A Mapping Rules {'JSON' if file_type == 'application/json' else 'CSV'} is being generated.",
            )
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data."}, status=400)
        except Exception:
            return JsonResponse({"error": "Internal server error."}, status=500)

        return HttpResponse(status=202)

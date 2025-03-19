import json

from django.conf import settings
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
from shared.services.azurequeue import add_message
from shared.services.storage_service import StorageService

from .models import FileDownload
from .serializers import FileDownloadSerializer

storage_service = StorageService()


class FileDownloadView(GenericAPIView, ListModelMixin, RetrieveModelMixin):
    serializer_class = FileDownloadSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    pagination_class = CustomPagination
    permission_classes = [IsAuthenticated]
    ordering = "-created_at"

    def get_queryset(self):
        scan_report_id = self.kwargs["scanreport_pk"]
        scan_report = get_object_or_404(ScanReport, pk=scan_report_id)

        return FileDownload.objects.filter(scan_report=scan_report)

    def get(self, request, *args, **kwargs):
        if "pk" in kwargs:
            entity = get_object_or_404(FileDownload, pk=kwargs["pk"])
            file = storage_service.get_blob(entity.file_url, "rules-exports")

            response = HttpResponse(file, content_type="application/octet-stream")
            response["Content-Disposition"] = f'attachment; filename="{entity.name}"'
            return response

        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Requests a file to be generated for download by sending a message to the Rules Export Queue.
        """
        try:
            body = request.data
            scan_report_id = body.get("scan_report_id")
            file_type = body.get("file_type")

            if not scan_report_id or not file_type:
                return JsonResponse(
                    {"error": "scan_report_id and file_type are required."}, status=400
                )

            msg = {
                "scan_report_id": scan_report_id,
                "user_id": request.user.id,
                "file_type": file_type,
            }

            add_message(settings.WORKERS_RULES_EXPORT_NAME, msg)
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

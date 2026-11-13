from importlib.metadata import version

from api.mixins import ScanReportPermissionMixin
from drf_spectacular.utils import extend_schema
from mapping.models import ScanReport
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from registry.serializers import (
    RegistryImportAcceptedSerializer,
    ScanReportRegistryPublishSerializer,
)
from registry.services import submit_direct_publish


class ScanReportRegistryPublishView(ScanReportPermissionMixin, GenericAPIView):
    """
    Publish a scan report's mappings to the Carrot Mappings Registry.

    Requires edit or admin rights on the scan report. The import runs
    asynchronously: the response carries the ImportJob id to poll.
    """

    queryset = ScanReport.objects.all()
    serializer_class = ScanReportRegistryPublishSerializer
    http_method_names = ["post"]

    @extend_schema(
        request=ScanReportRegistryPublishSerializer,
        responses={202: RegistryImportAcceptedSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job, _ = submit_direct_publish(
            scan_report=self.scan_report,
            user=request.user,
            metadata=serializer.validated_data,
            mapper_version=version("api"),
        )

        return Response(
            RegistryImportAcceptedSerializer(
                {"import_job_id": job.id, "status": job.status}
            ).data,
            status=status.HTTP_202_ACCEPTED,
        )

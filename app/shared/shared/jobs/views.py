from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin

from .models import Job
from .serializers import JobSerializer


class JobView(GenericAPIView, ListModelMixin):
    """
    View for list of Jobs records of a specific object.

    This view allows filtering Jobs record based on the scan_report_id or scan_report_table_id
    passed as a URL parameter and the stage passed as a query parameter.
    """

    queryset = Job.objects.all().order_by("-created_at")
    filter_backends = [DjangoFilterBackend]
    serializer_class = JobSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        scan_report_id = self.kwargs.get("pk")

        queryset = self.queryset
        stage = self.request.query_params.get("stage")
        if scan_report_id is not None:
            if stage == "upload":
                return queryset.filter(scan_report_id=scan_report_id, stage=1)
            if stage == "download":
                return queryset.filter(scan_report_id=scan_report_id, stage=5)
            return queryset.filter(scan_report_id=scan_report_id)

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin

from .models import Job
from .serializers import JobSerializer


class JobView(GenericAPIView, ListModelMixin):
    """
    View for listing Job records associated with a specific object.

    This view is designed to retrieve and filter Job records based on the following criteria:
    - `scan_report_id`: Passed as a URL parameter (`pk`), it identifies the specific scan report 
      to which the Job records are related.
    - `stage`: Passed as a query parameter, it specifies the stage of the Job records to filter. 
      Supported stages include:
        - `upload`: Filters Job records with stage value 1.
        - `download`: Filters Job records with stage value 5.
        - If no stage is provided, all Job records associated with the given `scan_report_id` 
          are returned.

    The queryset is ordered by the `created_at` field in descending order, ensuring the most 
    recently created Job records appear first.

    This view supports GET requests to list the filtered Job records.
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

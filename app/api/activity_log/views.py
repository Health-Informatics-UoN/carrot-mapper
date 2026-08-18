from api.mixins import ScanReportPermissionMixin
from api.paginations import CustomPagination
from django.db.models import Q
from django.shortcuts import get_object_or_404
from mapping.models import Dataset, ScanReport
from mapping.permissions import CanAdmin, CanEdit, CanView
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response

from .models import ActivityLog, ScopeType
from .serializers import ActivityLogSerializer


class ScanReportActivityLogView(
    ScanReportPermissionMixin, GenericAPIView, ListModelMixin
):
    """
    Lists ActivityLog entries scoped to a single Scan Report, newest first.
    """

    serializer_class = ActivityLogSerializer
    pagination_class = CustomPagination
    http_method_names = ["get"]

    def get_queryset(self):
        return ActivityLog.objects.filter(
            scope_type=ScopeType.SCAN_REPORT, scope_id=self.kwargs["pk"]
        ).order_by("-occurred_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Every row here belongs to `self.scan_report` (set by
        # ScanReportPermissionMixin), so the serializer never needs to
        # look the name up itself.
        context["scan_report_names"] = {self.scan_report.id: self.scan_report.dataset}
        return context

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class DatasetActivityLogView(GenericAPIView, ListModelMixin):
    """
    Lists ActivityLog entries for a Dataset, newest first.

    This is a roll-up: every event today is emitted against a Scan Report
    (see activity_log.models.Verb), so this view aggregates the logs of
    every Scan Report under the dataset, in addition to any log entries
    recorded directly against the dataset itself.
    """

    serializer_class = ActivityLogSerializer
    pagination_class = CustomPagination
    permission_classes = [CanView | CanAdmin | CanEdit]
    http_method_names = ["get"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.dataset = get_object_or_404(Dataset, pk=self.kwargs["pk"])
        self.check_object_permissions(request, self.dataset)

    def get_queryset(self):
        scan_report_ids = ScanReport.objects.filter(
            parent_dataset_id=self.dataset.id
        ).values_list("id", flat=True)
        return ActivityLog.objects.filter(
            Q(scope_type=ScopeType.DATASET, scope_id=self.dataset.id)
            | Q(scope_type=ScopeType.SCAN_REPORT, scope_id__in=scan_report_ids)
        ).order_by("-occurred_at")

    def list(self, request, *args, **kwargs):
        """
        Overridden (rather than relying on the serializer's per-row
        fallback query) to resolve every scan report name on this page in
        one query: a dataset's log feed can span many different scan
        reports, so a per-row lookup would be an N+1.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        logs = page if page is not None else queryset

        scan_report_ids = {
            log.scope_id for log in logs if log.scope_type == ScopeType.SCAN_REPORT
        }
        scan_report_names = dict(
            ScanReport.objects.filter(id__in=scan_report_ids).values_list(
                "id", "dataset"
            )
        )

        serializer = self.get_serializer(
            logs,
            many=True,
            context={
                **self.get_serializer_context(),
                "scan_report_names": scan_report_names,
            },
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

from mapping.models import ScanReport
from rest_framework import serializers

from .models import ActivityLog, ScopeType


class ActivityLogSerializer(serializers.ModelSerializer):
    # Resolved at render time rather than stored on the row, matching the
    # no-GenericForeignKey design: `scope_id` is a plain int, so the name
    # has to be looked up here. Callers that already know the scan report
    # (e.g. the single-scan-report log view) can avoid the lookup by
    # passing a `scan_report_names` map in the serializer context.
    scan_report_name = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "scope_type",
            "scope_id",
            "verb",
            "occurred_at",
            "actor_id",
            "actor_label",
            "object_type",
            "object_id",
            "detail",
            "scan_report_name",
        ]

    def get_scan_report_name(self, obj: ActivityLog):
        if obj.scope_type != ScopeType.SCAN_REPORT:
            return None

        scan_report_names = self.context.get("scan_report_names")
        if scan_report_names is not None:
            return scan_report_names.get(obj.scope_id)

        return (
            ScanReport.objects.filter(id=obj.scope_id)
            .values_list("dataset", flat=True)
            .first()
        )

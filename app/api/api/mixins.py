from django.shortcuts import get_object_or_404
from mapping.models import ScanReport
from mapping.permissions import CanAdmin, CanEditOrAdmin, CanView


class ScanReportPermissionMixin:
    """
    Mixin to handle permission checks for Scan Reports.

    This mixin provides a method to fetch a Scan Report and apply
    permission checks based on the request method.
    """

    permission_classes_by_method = {
        "GET": [CanView],
        "POST": [CanView],
        "PUT": [CanEditOrAdmin],
        "PATCH": [CanEditOrAdmin],
        "DELETE": [CanAdmin],
    }

    def initial(self, request, *args, **kwargs):
        """
        Ensures that self.scan_report is set before get_queryset is called.
        """
        self.scan_report = get_object_or_404(ScanReport, pk=self.kwargs["pk"])
        super().initial(request, *args, **kwargs)

    def get_permissions(self):
        """
        Returns the list of permissions that the current action requires.
        Handles cases where self.scan_report is not set (e.g., during schema generation).
        """
        method = self.request.method
        self.permission_classes = self.permission_classes_by_method.get(
            method, [CanView]
        )

        permissions = [permission() for permission in self.permission_classes]

        # Skip object-level permission checks if self.scan_report is not set
        if not hasattr(self, "scan_report") or self.scan_report is None:
            return permissions

        # Perform object-level permission checks
        for permission in permissions:
            if not permission.has_object_permission(
                self.request, self, self.scan_report
            ):
                self.permission_denied(
                    self.request, message=getattr(permission, "message", None)
                )

        return permissions

from django.shortcuts import get_object_or_404
from shared.mapping.models import ScanReport
from shared.mapping.permissions import CanAdmin, CanEditOrAdmin, CanView


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
        """

        method = self.request.method
        self.permission_classes = self.permission_classes_by_method.get(
            method, [CanView]
        )

        permissions = [permission() for permission in self.permission_classes]

        for permission in permissions:
            if not permission.has_object_permission(
                self.request, self, self.scan_report
            ):
                self.permission_denied(
                    self.request, message=getattr(permission, "message", None)
                )

        return permissions

from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from shared.mapping.models import ScanReport
from shared.mapping.permissions import CanAdmin, CanEditOrAdmin, CanView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


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
        if not self.is_schema_or_docs_request(request):
            # Fetch the scan_report only if it's a normal request
            self.scan_report = get_object_or_404(ScanReport, pk=self.kwargs["pk"])

        super().initial(request, *args, **kwargs)

    def get_permissions(self):
        """
        Returns the list of permissions that the current action requires.
        """
        # Skip permission checks for schema or docs request
        if self.is_schema_or_docs_request(self.request):
            return [AllowAny()]

        method = self.request.method
        self.permission_classes = self.permission_classes_by_method.get(
            method, [CanView]
        )

        permissions = [permission() for permission in self.permission_classes]

        # Ensure scan_report exists before checking permissions
        if hasattr(self, "scan_report"):
            for permission in permissions:
                if not permission.has_object_permission(
                    self.request, self, self.scan_report
                ):
                    self.permission_denied(
                        self.request, message=getattr(permission, "message", None)
                    )

        return permissions

    def is_schema_or_docs_request(self, request):
        """
        Helper method to check if the request is for schema or documentation views.
        """
        if request.resolver_match:
            view_name = request.resolver_match.view_name
            return view_name in [
                "schema",
                "schema-swagger-ui",
                "schema-redoc",
                "schema-json",
            ]

        return False

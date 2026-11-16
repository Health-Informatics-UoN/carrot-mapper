from django.urls import path

from registry import views

urlpatterns = [
    path("licenses/", views.LicenseListView.as_view(), name="registry-license-list"),
    path(
        "scanreports/<int:pk>/registry-publish/",
        views.ScanReportRegistryPublishView.as_view(),
        name="registry-scan-report-publish",
    ),
]

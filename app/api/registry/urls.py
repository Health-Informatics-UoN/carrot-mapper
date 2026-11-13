from django.urls import path

from registry import views

urlpatterns = [
    path(
        "scanreports/<int:pk>/registry-publish/",
        views.ScanReportRegistryPublishView.as_view(),
        name="registry-scan-report-publish",
    ),
]

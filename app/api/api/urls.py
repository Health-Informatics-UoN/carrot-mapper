from api import views
from api.deprecated_router import router as deprecated_router
from django.urls import include, path
from shared.files.views import FileDownloadView
from shared.jobs.views import JobView

from .deprecated_urls import urlpatterns as deprecated_urlpatterns

urlpatterns = [
    path("", include(deprecated_router.urls)),
    path("v2/datasets/", include("datasets.urls")),
    path("projects/", include("projects.urls")),
    path(
        "v2/scanreports/", views.ScanReportIndexV2.as_view(), name="scan-report-index"
    ),
    path(
        "v2/scanreports/concepts/",
        views.ScanReportConceptListV2.as_view(),
        name="scan-report-concepts",
    ),
    path(
        "v2/scanreports/concepts/<int:pk>/",
        views.ScanReportConceptDetailV2.as_view(),
        name="scan-report-concepts",
    ),
    path(
        "v2/scanreports/<int:pk>/",
        views.ScanReportDetailV2.as_view(),
        name="scan-report-detail",
    ),
    path(
        "v2/scanreports/<int:pk>/jobs/",
        JobView.as_view(),
        name="scan-report-jobs",
    ),
    path(
        "v2/scanreports/<int:pk>/tables/",
        views.ScanReportTableIndexV2.as_view(),
        name="scan-report-tables",
    ),
    path(
        r"v2/scanreports/<int:pk>/download/",
        views.DownloadScanReportViewSet.as_view({"get": "list"}),
    ),
    path(
        r"v2/scanreports/<int:pk>/analyse/",
        views.AnalyseRulesV2.as_view(),
        name="scan-reports-analyse",
    ),
    path(
        "v2/scanreports/<int:pk>/permissions/",
        views.ScanReportPermissionView.as_view(),
        name="scan-report-permissions",
    ),
    path(
        "scanreports/<int:pk>/mapping_rules/",
        views.MappingRulesList.as_view(),
        name="scan-report-rules-download-svg",
    ),
    path(
        "v2/scanreports/<int:pk>/rules/",
        views.RulesListV2.as_view(),
        name="scan-report-rules-list",
    ),
    path(
        "v2/scanreports/<int:pk>/rules/summary",
        views.SummaryRulesListV2.as_view(),
        name="scan-report-rules-list-summary",
    ),
    path(
        "v2/scanreports/<int:scanreport_pk>/rules/downloads/",
        FileDownloadView.as_view(),
        name="scan-reports-downloads",
    ),
    path(
        "v2/scanreports/<int:scanreport_pk>/rules/downloads/<int:pk>",
        FileDownloadView.as_view(),
        name="scan-report-downloads-get",
    ),
    path(
        "v2/scanreports/<int:pk>/tables/<int:table_pk>/",
        views.ScanReportTableDetailV2.as_view(),
        name="scan-report-table-detail",
    ),
    path(
        "v2/scanreports/<int:pk>/tables/<int:table_pk>/fields/",
        views.ScanReportFieldIndexV2.as_view(),
        name="scan-report-fields",
    ),
    path(
        "v2/scanreports/<int:pk>/tables/<int:table_pk>/fields/<int:field_pk>/",
        views.ScanReportFieldDetailV2.as_view(),
        name="scan-report-fields-detail",
    ),
    path(
        "v2/scanreports/<int:pk>/tables/<int:table_pk>/fields/<int:field_pk>/values/",
        views.ScanReportValueListV2.as_view(),
        name="scan-report-values",
    ),
    path(r"user/me/", views.UserDetailView.as_view(), name="currentuser"),
    path(r"v2/users/", views.UserViewSet.as_view(), name="users-list"),
    path(r"v2/usersfilter/", views.UserFilterViewSet.as_view(), name="usersfilter"),
    path(r"v2/datapartners/", views.DataPartnerViewSet.as_view(), name="datapartners"),
    path(
        r"v2/omop/conceptsfilter",
        views.ConceptFilterViewSetV2.as_view(),
        name="v2conceptsfilter",
    ),
]

urlpatterns += deprecated_urlpatterns

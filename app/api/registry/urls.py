from django.urls import path

from registry import views

urlpatterns = [
    # Read: discovery, search, filter
    path("licenses/", views.LicenseListView.as_view(), name="registry-license-list"),
    path(
        "mapping-sets/",
        views.MappingSetListView.as_view(),
        name="registry-mapping-set-list",
    ),
    path(
        "mapping-sets/<uuid:pk>/",
        views.MappingSetDetailView.as_view(),
        name="registry-mapping-set-detail",
    ),
    path(
        "mapping-sets/<uuid:pk>/download/",
        views.MappingSetDownloadView.as_view(),
        name="registry-mapping-set-download",
    ),
    path(
        "mapping-sets/<uuid:pk>/mappings/",
        views.MappingSetMappingsView.as_view(),
        name="registry-mapping-set-mappings",
    ),
    path("mappings/", views.MappingListView.as_view(), name="registry-mapping-list"),
    path("terms/", views.TermListView.as_view(), name="registry-term-list"),
    path(
        "terms/<int:pk>/", views.TermDetailView.as_view(), name="registry-term-detail"
    ),
    path(
        "terms/<int:pk>/mappings/",
        views.TermMappingsView.as_view(),
        name="registry-term-mappings",
    ),
    path(
        "predicates/",
        views.PredicateListView.as_view(),
        name="registry-predicate-list",
    ),
    path(
        "justifications/",
        views.MappingJustificationListView.as_view(),
        name="registry-justification-list",
    ),
    # Write
    path("imports/", views.ImportJobListView.as_view(), name="registry-import-list"),
    path(
        "imports/<uuid:pk>/",
        views.ImportJobDetailView.as_view(),
        name="registry-import-detail",
    ),
    path(
        "mapping-sets/<uuid:pk>/publish/",
        views.MappingSetPublishView.as_view(),
        name="registry-mapping-set-publish",
    ),
    path(
        "mapping-sets/<uuid:pk>/withdraw/",
        views.MappingSetWithdrawView.as_view(),
        name="registry-mapping-set-withdraw",
    ),
    path(
        "scanreports/<int:pk>/registry-publish/",
        views.ScanReportRegistryPublishView.as_view(),
        name="registry-scan-report-publish",
    ),
]

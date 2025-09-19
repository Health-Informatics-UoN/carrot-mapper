from django.urls import path

from datasets import views

urlpatterns = [
    path(
        r"",
        views.DatasetIndex.as_view(),
        name="dataset_list",
    ),
    path(
        r"datasets_data_partners/",
        views.DatasetAndDataPartnerListView.as_view(),
        name="dataset_data_partners_list",
    ),
    path(
        r"<int:pk>/",
        views.DatasetDetail.as_view(),
        name="dataset_retrieve",
    ),
    path(
        "<int:pk>/permissions/",
        views.DatasetPermissionView.as_view(),
        name="dataset-permissions",
    ),
]

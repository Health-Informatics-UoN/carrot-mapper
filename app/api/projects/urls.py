from django.urls import path

from projects import views

urlpatterns = [
    path("", views.ProjectList.as_view(), name="project_list"),
    path(
        "<int:pk>/",
        views.ProjectDetail.as_view(),
        name="project_detail",
    ),
]

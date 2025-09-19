from api.paginations import CustomPagination
from django_filters.rest_framework import DjangoFilterBackend
from mapping.models import Project
from mapping.permissions import CanViewProject
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from projects.serializers import (
    ProjectDatasetSerializer,
    ProjectSerializer,
)


class ProjectList(ListAPIView):
    """
    API view to list all projects accessible to the authenticated user.

    This view supports filtering by project name and ordering by specific fields.
    It also supports pagination to handle large datasets efficiently.

    - If the `datasets` query parameter is provided, the response will include
      dataset-related information using the `ProjectDatasetSerializer`.
    - If the `dataset` query parameter is provided, the response will be filtered
      to include only projects associated with the specified dataset and where
      the authenticated user is a member.
    - Otherwise, it will return all projects where the authenticated user is a member.

    Query Parameters:
    - `datasets`: If present, uses `ProjectDatasetSerializer` for serialization.
    - `dataset`: Filters projects by the specified dataset ID.
    - `name`: Supports filtering by name using `in` or `icontains`.
    - `ordering`: Allows ordering by `id` or `name` (default is `-created_at`).

    Permissions:
    - Requires the user to be authenticated.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    pagination_class = CustomPagination
    filterset_fields = {"name": ["in", "icontains"]}
    ordering_fields = ["id", "name"]
    ordering = "-created_at"

    def get_serializer_class(self):
        if self.request.GET.get("datasets") is not None:
            return ProjectDatasetSerializer

        return ProjectSerializer

    def get_queryset(self):
        if dataset := self.request.GET.get("dataset"):
            return Project.objects.filter(
                datasets__exact=dataset, members__id=self.request.user.id
            ).distinct()

        return Project.objects.filter(members__id=self.request.user.id).distinct()


class ProjectDetail(RetrieveAPIView):
    """
    API view to retrieve detailed information about a single project.

    This view ensures that only users who are members of the project can access
    its details. If the user is not a member, a 403 Forbidden response is returned.

    Permissions:
    - Requires the user to have the `CanViewProject` permission.

    Response:
    - Returns detailed information about the project using the `ProjectSerializer`.
    """

    permission_classes = [CanViewProject]
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()

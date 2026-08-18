from api.paginations import CustomPagination
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from mapping.models import Project
from mapping.permissions import (
    CanAdminProject,
    CanViewProject,
    get_user_permissions_on_project,
)
from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.serializers import (
    ProjectCreateSerializer,
    ProjectDatasetSerializer,
    ProjectEditSerializer,
    ProjectSerializer,
)


class ProjectList(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    API view to list all projects accessible to the authenticated user, and
    to create new projects.

    This view supports filtering by project name and ordering by specific fields.
    It also supports pagination to handle large datasets efficiently.

    - If the `datasets` query parameter is provided, the response will include
      dataset-related information using the `ProjectDatasetSerializer`.
    - If the `dataset` query parameter is provided, the response will be filtered
      to include only projects associated with the specified dataset and where
      the authenticated user is a member.
    - Otherwise, it will return all projects where the authenticated user is a member.
    - On POST, any authenticated user may create a Project. The creator is
      automatically added to the Project's `members` and `admins`.

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
        if self.request.method == "POST":
            return ProjectCreateSerializer
        if self.request.GET.get("datasets") is not None:
            return ProjectDatasetSerializer

        return ProjectSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        user_id = self.request.user.id
        admins = serializer.initial_data.get("admins") or []
        members = serializer.initial_data.get("members") or []
        if user_id not in admins:
            admins = admins + [user_id]
        if user_id not in members:
            members = members + [user_id]
        serializer.save(admins=admins, members=members)

    def get_queryset(self):
        if dataset := self.request.GET.get("dataset"):
            return Project.objects.filter(
                datasets__exact=dataset, members__id=self.request.user.id
            ).distinct()

        return Project.objects.filter(members__id=self.request.user.id).distinct()


class ProjectDetail(GenericAPIView, RetrieveModelMixin, UpdateModelMixin):
    """
    API view to retrieve and update detailed information about a single project.

    Permissions:
    - GET: Requires `CanViewProject`.
    - PATCH, PUT: Requires `CanAdminProject`.

    Response:
    - Returns detailed information about the project using the `ProjectSerializer`
      (GET) or `ProjectEditSerializer` (PATCH, PUT).
    """

    queryset = Project.objects.all()

    def initial(self, request, *args, **kwargs):
        self.permission_classes = [CanViewProject]
        if self.request.method in ["PATCH", "PUT"]:
            self.permission_classes = [CanAdminProject]
        return super().initial(request)

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return ProjectEditSerializer
        return ProjectSerializer

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class ProjectPermissionView(APIView):
    """
    API for retrieving the permissions a user has on a specific project.

    Methods:
        get(request, pk):
            Handles GET requests to retrieve the user's permissions for
            the project identified by the primary key (pk).
    """

    @extend_schema(
        responses={
            200: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        description="Get the permissions for a project.",
    )
    def get(self, request, pk):
        permissions = get_user_permissions_on_project(request, pk)

        return Response({"permissions": permissions}, status=status.HTTP_200_OK)

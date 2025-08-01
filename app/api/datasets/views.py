import os

from api.paginations import CustomPagination
from datasets.serializers import (
    DatasetAndDataPartnerViewSerializer,
    DatasetEditSerializer,
    DatasetViewSerializerV2,
    DatasetCreateSerializerV2,
)
from django.db.models.query_utils import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from mapping.models import Dataset, VisibilityChoices
from mapping.permissions import (
    CanAdmin,
    CanEdit,
    CanView,
    get_user_permissions_on_dataset,
)


class DatasetIndex(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    API view to list all datasets with support for filtering and pagination.

    This view allows users to retrieve a list of datasets based on specific
    filter criteria such as dataset ID, data partner, and visibility status.
    It also supports pagination to handle large datasets efficiently.

    - If the request method is POST, the `DatasetCreateSerializerV2` is used
      to handle dataset creation.
    - For GET requests, the `DatasetViewSerializerV2` is used to serialize
      the dataset data.

    Filtering options:
    - `id`: Filter datasets by their IDs.
    - `data_partner`: Filter datasets by their associated data partner.
    - `hidden`: Filter datasets based on their hidden status.

    The queryset returned depends on the user's permissions and visibility
    settings of the datasets.
    """

    serializer_class = DatasetViewSerializerV2
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "id": ["in"],
        "data_partner": ["in", "exact"],
        "hidden": ["in", "exact"],
    }

    def get_serializer_class(self):
        if self.request.method in ["POST"]:
            return DatasetCreateSerializerV2
        return super().get_serializer_class()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        admins = serializer.initial_data.get("admins")
        # If no admins given, add the user uploading the dataset
        if not admins:
            serializer.save(admins=[self.request.user])
        # If the user is not in the admins, add them
        elif self.request.user.id not in admins:
            serializer.save(admins=admins + [self.request.user.id])
        # All is well, save
        else:
            serializer.save()

    def get_queryset(self):
        """
        If the User is the `AZ_FUNCTION_USER`, return all Datasets.

        Else, return only the Datasets which are on projects a user is a member,
        which are "PUBLIC", or "RESTRICTED" Datasets that a user is a viewer of.
        """
        if self.request.user.username == os.getenv("AZ_FUNCTION_USER"):
            return Dataset.objects.all().distinct()

        return Dataset.objects.filter(
            Q(visibility=VisibilityChoices.PUBLIC)
            | Q(
                viewers=self.request.user.id,
                visibility=VisibilityChoices.RESTRICTED,
            )
            | Q(
                editors=self.request.user.id,
                visibility=VisibilityChoices.RESTRICTED,
            )
            | Q(
                admins=self.request.user.id,
                visibility=VisibilityChoices.RESTRICTED,
            ),
            project__members=self.request.user.id,
        ).distinct()


class DatasetAndDataPartnerListView(GenericAPIView, ListModelMixin):
    """
    API view to list all datasets with filtering, ordering, and
    pagination support.

    This view provides a list of datasets based on the user's access
    level and membership in projects. It supports filtering by various
    fields, ordering by specific attributes, and paginated responses.

    Attributes:
        serializer_class (DatasetAndDataPartnerViewSerializer): The
            serializer used to format the dataset data.
        pagination_class (CustomPagination): The pagination class used
            to paginate the dataset list.
        filter_backends (list): A list of filter backends used for
            filtering and ordering the dataset list.
        ordering_fields (list): Fields that can be used for ordering
            the dataset list.
        filterset_fields (dict): Fields that can be used for filtering
            the dataset list.
        ordering (str): Default ordering for the dataset list.

    Methods:
        get(request, *args, **kwargs):
            Handles GET requests to retrieve the list of datasets.

        get_queryset():
            Returns the queryset of datasets based on the user's access
            level:
            - If the user is the `AZ_FUNCTION_USER`, all datasets are
              returned.
            - Otherwise, only datasets that are public, restricted
              datasets the user has access to, or datasets in projects
              the user is a member of are returned.
    """

    serializer_class = DatasetAndDataPartnerViewSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["id", "name", "created_at", "visibility", "data_partner"]
    filterset_fields = {
        "id": ["in"],
        "hidden": ["in", "exact"],
        "name": ["in", "icontains"],
        "project": ["exact"],
    }
    ordering = "-created_at"

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        """
        If the User is the `AZ_FUNCTION_USER`, return all Datasets.

        Else, return only the Datasets which are on projects a user is a member,
        which are "PUBLIC", or "RESTRICTED" Datasets that a user is a viewer of.
        """

        if self.request.user.username == os.getenv("AZ_FUNCTION_USER"):
            return Dataset.objects.prefetch_related("data_partner").all().distinct()

        return (
            Dataset.objects.filter(
                Q(visibility=VisibilityChoices.PUBLIC)
                | Q(
                    viewers=self.request.user.id,
                    visibility=VisibilityChoices.RESTRICTED,
                )
                | Q(
                    editors=self.request.user.id,
                    visibility=VisibilityChoices.RESTRICTED,
                )
                | Q(
                    admins=self.request.user.id,
                    visibility=VisibilityChoices.RESTRICTED,
                ),
                project__members=self.request.user.id,
            )
            .prefetch_related("data_partner")
            .distinct()
            .order_by("-id")
        )


class DatasetDetail(
    GenericAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin
):
    """
    Dataset Detail View.

    This view provides detailed operations for a Dataset object,
    including retrieving, updating, and deleting. The permissions and
    serializers used are dynamically determined based on the HTTP
    method of the request.

    Inherits:
        - GenericAPIView: Base class for all API views.
        - RetrieveModelMixin: Adds retrieve functionality.
        - UpdateModelMixin: Adds update functionality.
        - DestroyModelMixin: Adds delete functionality.

    Permissions:
        - GET: Requires `CanView`, `CanAdmin`, or `CanEdit` permissions.
        - POST, PATCH, PUT: Requires `CanView` and either `CanAdmin` or
          `CanEdit` permissions.
        - DELETE: Requires `CanView` and `CanAdmin` permissions.

    Serializers:
        - DatasetEditSerializer: Used for POST, PATCH, PUT, and DELETE
          requests.
        - DatasetViewSerializerV2: Used for GET requests.

    Methods:
        - initial: Dynamically sets permissions based on the request
          method.
        - get_queryset: Returns the queryset filtered by the primary
          key (`pk`).
        - get_serializer_class: Determines the serializer class based
          on the request method.
        - get_serializer_context: Provides additional context for the
          serializer.
        - get: Handles GET requests to retrieve a dataset.
        - patch: Handles PATCH requests to partially update a dataset.
    """

    permission_classes = [CanView | CanAdmin | CanEdit]

    def initial(self, request, *args, **kwargs):
        self.permission_classes = [CanView | CanAdmin | CanEdit]
        if self.request.method in ["POST", "PATCH", "PUT"]:
            self.permission_classes = [CanView & (CanAdmin | CanEdit)]
        if self.request.method in ["DELETE"]:
            self.permission_classes = [CanView & CanAdmin]
        return super().initial(request)

    def get_queryset(self):
        return Dataset.objects.filter(id=self.kwargs.get("pk"))

    def get_serializer_class(self):
        if self.request.method in ["POST", "PATCH", "PUT", "DELETE"]:
            return DatasetEditSerializer
        return DatasetViewSerializerV2

    def get_serializer_context(self):
        return {"projects": self.request.data.get("projects")}

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class DatasetPermissionView(APIView):
    """
    API for retrieving the permissions a user has on a specific dataset.

    This view handles GET requests to fetch the permissions associated
    with a dataset for the currently authenticated user. Permissions
    are determined based on the user's role and access level for the
    specified dataset.

    Methods:
        get(request, pk):
            Handles GET requests to retrieve the user's permissions for
            the dataset identified by the primary key (pk).
    """

    @extend_schema(
        responses={
            200: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
        description="Get the permissions for a dataset.",
    )
    def get(self, request, pk):
        permissions = get_user_permissions_on_dataset(request, pk)

        return Response({"permissions": permissions}, status=status.HTTP_200_OK)

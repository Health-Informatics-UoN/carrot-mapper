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
from rest_framework import generics, status
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
from shared.mapping.models import Dataset, VisibilityChoices
from shared.mapping.permissions import (
    CanAdmin,
    CanEdit,
    CanView,
    get_user_permissions_on_dataset,
)


class DatasetIndex(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    API view to show all datasets.
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
    API view to show all datasets.
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
    Detail View for Datasets.

    Allows for update and deleting.
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
    API for permissions a user has on a specific dataset.
    """

    def get(self, request, pk):
        permissions = get_user_permissions_on_dataset(request, pk)

        return Response({"permissions": permissions}, status=status.HTTP_200_OK)

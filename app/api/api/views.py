import datetime
import os
import random
import string
from importlib.metadata import version
from typing import Any, Optional

from data.models import Concept
from datasets.serializers import DataPartnerSerializer
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from jobs.models import Job, JobStage, StageStatus
from mapping.models import (
    DataDictionary,
    DataPartner,
    MappingRule,
    OmopField,
    ScanReport,
    ScanReportConcept,
    ScanReportField,
    ScanReportTable,
    ScanReportValue,
)
from mapping.permissions import get_user_permissions_on_scan_report
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from services.rules import (
    _find_destination_table,
    save_mapping_rules,
)
from services.rules_export import (
    get_mapping_rules_json,
    get_mapping_rules_list,
    make_dag,
)
from services.storage_service import StorageService
from services.worker_service import get_worker_service

from api.filters import ScanReportAccessFilter, ScanReportValueFilter
from api.mixins import ScanReportPermissionMixin
from api.paginations import CustomPagination
from api.serializers import (
    ConceptSerializerV2,
    GetRulesAnalysis,
    ScanReportConceptDetailSerializerV3,
    ScanReportConceptSerializer,
    ScanReportCreateSerializer,
    ScanReportEditSerializer,
    ScanReportFieldEditSerializer,
    ScanReportFieldListSerializerV2,
    ScanReportFilesSerializer,
    ScanReportTableEditSerializer,
    ScanReportTableListSerializerV2,
    ScanReportValueViewSerializerV2,
    ScanReportValueViewSerializerV3,
    ScanReportViewSerializerV2,
    UserSerializer,
)

storage_service = StorageService()
worker_service = get_worker_service()


class DataPartnerViewSet(GenericAPIView, ListModelMixin):
    """
    A viewset for handling DataPartner objects.

    This viewset provides a GET method to retrieve a list of all
    DataPartner objects using the ListModelMixin.

    Attributes:
        queryset (QuerySet): A queryset containing all DataPartner objects.
        serializer_class (Serializer): The serializer class used for
            serializing and deserializing DataPartner objects.

    Methods:
        get(request, *args, **kwargs):
            Handles GET requests to return a list of DataPartner objects.
    """

    queryset = DataPartner.objects.all().order_by("name")
    serializer_class = DataPartnerSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class ConceptFilterViewSetV2(GenericAPIView, ListModelMixin):
    """
    A viewset for filtering and listing Concept objects.

    This viewset provides functionality to filter and paginate Concept
    objects based on specified fields and their values. It uses
    DjangoFilterBackend for filtering and a custom pagination class for
    paginating the results.

    Attributes:
        queryset (QuerySet): The base queryset for retrieving Concept
            objects, ordered by `concept_id`.
        serializer_class (Serializer): The serializer class used for
            serializing Concept objects.
        filter_backends (list): A list of filter backends to apply to
            the queryset.
        pagination_class (Pagination): The pagination class used for
            paginating the results.
        filterset_fields (dict): A dictionary defining the fields that
            can be filtered and the types of filtering allowed for each
            field.

    Methods:
        get(request, *args, **kwargs):
            Handles GET requests to retrieve a filtered and paginated
            list of Concept objects.
    """

    queryset = Concept.objects.all().order_by("concept_id")
    serializer_class = ConceptSerializerV2
    filter_backends = [DjangoFilterBackend]
    pagination_class = CustomPagination
    filterset_fields = {
        "concept_id": ["in", "exact"],
        "concept_code": ["in", "exact"],
        "vocabulary_id": ["in", "exact"],
    }

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class UserViewSet(GenericAPIView, ListModelMixin):
    """
    A viewset for handling user-related API requests.

    This viewset provides a GET method to retrieve a list of users.

    Attributes:
        queryset (QuerySet): The queryset containing all User objects.
        serializer_class (Serializer): The serializer class used to
            serialize User objects.

    Methods:
        get(request, *args, **kwargs):
            Handles GET requests to return a list of users.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class UserFilterViewSet(GenericAPIView, ListModelMixin):
    """
    A viewset for filtering and listing User objects.

    Supports filtering by `id` (exact, in) and `is_active` (exact).

    Methods:
        get(request, *args, **kwargs): Returns a filtered list of users.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["id", "username"]
    filterset_fields = {"id": ["in", "exact"], "is_active": ["exact"]}

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class UserDetailView(APIView):
    """
    A view that handles retrieving the details of the authenticated user.

    This view requires the user to be authenticated and uses the
    `IsAuthenticated` permission class to enforce this. When a GET
    request is made to this view, it serializes the authenticated
    user's data using the `UserSerializer` and returns it in the
    response.

    Methods:
        get(request, *args, **kwargs):
            Handles GET requests. Serializes the authenticated user's
            data and returns it in the response.

    Attributes:
        permission_classes (list): A list of permission classes that
            restrict access to authenticated users only.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        description="Retrieve the details of the authenticated user.",
    )
    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class ScanReportIndexV2(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    A custom viewset for managing and listing scan reports with
    enhanced functionality for version 2.

    This viewset extends the base functionality to include:
    - Advanced filtering options for scan reports based on various fields.
    - Custom ordering capabilities to sort scan reports by specific
      attributes.
    - Integration with a custom pagination class for efficient data
      retrieval.

    Features:
    - Supports filtering by fields such as `hidden`, `dataset`,
      `upload_status`, and more.
    - Allows ordering by attributes like `id`, `name`, `created_at`, and
      `dataset`.
    - Provides a seamless interface for retrieving and creating scan
      reports.

    Methods:
    - `get`: Handles GET requests to retrieve a paginated and filtered
      list of scan reports.
    - `post`: Handles POST requests to create new scan reports with file
      uploads.
    """

    queryset = ScanReport.objects.all()
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [
        DjangoFilterBackend,
        OrderingFilter,
        ScanReportAccessFilter,
    ]
    filterset_fields = {
        "hidden": ["exact"],
        "dataset": ["in", "icontains"],
        "upload_status__value": ["in"],
        "mapping_status__value": ["in"],
        "parent_dataset": ["exact"],
    }
    ordering_fields = [
        "id",
        "name",
        "created_at",
        "dataset",
        "parent_dataset",
    ]
    pagination_class = CustomPagination
    ordering = "-created_at"

    @extend_schema(responses=ScanReportViewSerializerV2)
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_scan_report_file(self, request):
        return request.data.get("scan_report_file", None)

    def get_serializer_class(self):
        if self.request.method in ["GET"]:
            return ScanReportViewSerializerV2
        if self.request.method in ["POST"]:
            return ScanReportFilesSerializer
        if self.request.method in ["DELETE", "PATCH", "PUT"]:
            return ScanReportEditSerializer
        return super().get_serializer_class()

    def post(self, request, *args, **kwargs):
        non_file_serializer = ScanReportCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not non_file_serializer.is_valid():
            return Response(
                non_file_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        file_serializer = self.get_serializer(data=request.FILES)
        if not file_serializer.is_valid():
            return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(file_serializer, non_file_serializer)
        headers = self.get_success_headers(file_serializer.data)
        return Response(
            file_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer, non_file_serializer):
        validatedFiles = serializer.validated_data
        validatedData = non_file_serializer.validated_data
        # List all the validated data and files
        valid_data_dictionary_file = validatedFiles.get("data_dictionary_file")
        valid_scan_report_file = validatedFiles.get("scan_report_file")
        valid_visibility = validatedData.get("visibility")
        valid_viewers = validatedData.get("viewers")
        valid_editors = validatedData.get("editors")
        valid_dataset = validatedData.get("dataset")
        valid_parent_dataset = validatedData.get("parent_dataset")

        rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        dt = "{:%Y%m%d-%H%M%S}".format(datetime.datetime.now())

        # Create an entry in ScanReport for the uploaded Scan Report
        scan_report = ScanReport.objects.create(
            dataset=valid_dataset,
            parent_dataset=valid_parent_dataset,
            name=storage_service.modify_filename(valid_scan_report_file, dt, rand),
            visibility=valid_visibility,
        )

        scan_report.author = self.request.user
        scan_report.save()

        # Add viewers to the scan report if specified
        if sr_viewers := valid_viewers:
            scan_report.viewers.add(*sr_viewers)

        # Add editors to the scan report if specified
        if sr_editors := valid_editors:
            scan_report.editors.add(*sr_editors)

        # Spreadsheet Content Type
        spreadsheet_content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # If there's no data dictionary supplied, only upload the scan report
        # Set data_dictionary_blob in Azure message to None
        if str(valid_data_dictionary_file) == "None":
            message_body = {
                "scan_report_id": scan_report.id,
                "scan_report_blob": scan_report.name,
                "data_dictionary_blob": "None",
            }

            storage_service.upload_file(
                scan_report.name,
                "scan-reports",
                valid_scan_report_file,
                spreadsheet_content_type,
                use_read_method=False,
            )

        else:
            data_dictionary = DataDictionary.objects.create(
                name=f"{os.path.splitext(str(valid_data_dictionary_file))[0]}"
                f"_{dt}{rand}.csv"
            )
            data_dictionary.save()
            scan_report.data_dictionary = data_dictionary
            scan_report.save()

            message_body = {
                "scan_report_id": scan_report.id,
                "scan_report_blob": scan_report.name,
                "data_dictionary_blob": data_dictionary.name,
            }

            storage_service.upload_file(
                scan_report.name,
                "scan-reports",
                valid_scan_report_file,
                spreadsheet_content_type,
                use_read_method=False,
            )
            storage_service.upload_file(
                data_dictionary.name,
                "data-dictionaries",
                valid_data_dictionary_file,
                "text/csv",
                use_read_method=False,
            )

        # send to the workers service
        worker_service.trigger_scan_report_processing(message_body)


class ScanReportDetailV2(
    ScanReportPermissionMixin,
    GenericAPIView,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
):
    """
    A view for handling detailed operations on ScanReport objects.

    This class-based view provides functionality for retrieving,
    updating, and deleting ScanReport objects. It uses different
    serializers based on the HTTP method of the request.

    Inherits:
        - ScanReportPermissionMixin: Mixin to handle permissions for
          ScanReport objects.
        - GenericAPIView: Base class for generic API views.
        - RetrieveModelMixin: Mixin to add retrieve functionality.
        - UpdateModelMixin: Mixin to add update functionality.
        - DestroyModelMixin: Mixin to add delete functionality.

    Attributes:
        queryset (QuerySet): The queryset of ScanReport objects.
        serializer_class (Serializer): The default serializer class for
            the view.

    Methods:
        get_serializer_class():
            Returns the appropriate serializer class based on the HTTP
            method.

        get(request, *args, **kwargs):
            Handles GET requests to retrieve a ScanReport object.

        patch(request, *args, **kwargs):
            Handles PATCH requests to partially update a ScanReport
            object.

        delete(request, *args, **kwargs):
            Handles DELETE requests to delete a ScanReport object.

        perform_destroy(instance):
            Deletes the given ScanReport instance and its associated
            data from the storage service.
    """

    queryset = ScanReport.objects.all()
    serializer_class = ScanReportViewSerializerV2

    def get_serializer_class(self):
        if self.request.method in ["GET"]:
            return ScanReportViewSerializerV2
        if self.request.method in ["POST"]:
            return ScanReportFilesSerializer
        if self.request.method in ["DELETE", "PATCH", "PUT"]:
            return ScanReportEditSerializer
        return super().get_serializer_class()

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def perform_destroy(self, instance):
        try:
            storage_service.delete_file(instance.name, "scan-reports")
        except Exception as e:
            raise Exception(f"Error deleting scan report: {e}")
        if instance.data_dictionary:
            try:
                storage_service.delete_file(
                    instance.data_dictionary.name, "data-dictionaries"
                )
            except Exception as e:
                raise Exception(f"Error deleting data dictionary: {e}")
        instance.delete()


class ScanReportTableIndexV2(ScanReportPermissionMixin, GenericAPIView, ListModelMixin):
    """
    ScanReportTableIndexV2 is a view that provides a paginated list of
    Scan Report Tables associated with a specific Scan Report. It
    supports filtering, ordering, and pagination.

    Features:
    - **Filtering**: Allows filtering by the `name` field using
      case-insensitive containment (`icontains`).
    - **Ordering**: Supports ordering by `name`, `person_id`, and
      `date_event`. Default ordering is by `-created_at`.
    - **Pagination**: Utilizes a custom pagination class
      (`CustomPagination`) for paginated responses.

    Attributes:
    - `filterset_fields`: Defines the fields available for filtering.
    - `filter_backends`: Specifies the backends used for filtering and
      ordering.
    - `ordering_fields`: Lists the fields available for ordering.
    - `pagination_class`: Specifies the pagination class to be used.
    - `ordering`: Defines the default ordering for the queryset.
    - `serializer_class`: Specifies the serializer used for serializing
      the response data.

    Methods:
    - `get`: Handles GET requests and returns a paginated list of Scan
      Report Tables.
    - `get_queryset`: Returns the queryset of Scan Report Tables
      filtered by the associated Scan Report.
    """

    filterset_fields = {
        "name": ["icontains"],
    }
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["name", "person_id", "date_event"]
    pagination_class = CustomPagination
    ordering = "-created_at"
    serializer_class = ScanReportTableListSerializerV2

    @extend_schema(responses=ScanReportTableListSerializerV2)
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return ScanReportTable.objects.filter(scan_report=self.scan_report)


class ScanReportTableDetailV2(
    ScanReportPermissionMixin, GenericAPIView, RetrieveModelMixin, UpdateModelMixin
):
    """
    A view for handling detailed operations on ScanReportTable objects.

    This view provides functionality for retrieving and updating
    ScanReportTable instances. It uses different serializers for GET and
    modification requests (PUT, PATCH, DELETE). Additionally, it triggers
    background jobs for mapping rules when a partial update (PATCH) is
    performed.

    Attributes:
        queryset (QuerySet): The queryset of ScanReportTable objects.
        serializer_class (Serializer): The default serializer class for
            the view.

    Methods:
        get_object():
            Retrieves a ScanReportTable instance based on the provided
            table_pk.

        get(request, *args, **kwargs):
            Handles GET requests to retrieve a ScanReportTable instance.

        get_serializer_class():
            Determines the serializer class to use based on the request
            method.

        patch(request, *args, **kwargs):
            Handles PATCH requests to partially update a ScanReportTable
            instance. Deletes existing mapping rules, triggers
            background jobs for mapping, and ensures no duplicate jobs
            are running for the same table.
    """

    queryset = ScanReportTable.objects.all()
    serializer_class = ScanReportTableListSerializerV2

    def get_object(self):
        return get_object_or_404(self.queryset, pk=self.kwargs["table_pk"])

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.request.method in ["GET", "POST"]:
            # use the view serialiser if on GET requests
            return ScanReportTableListSerializerV2
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            # use the edit serialiser when the user tries to alter the scan report
            return ScanReportTableEditSerializer
        return super().get_serializer_class()

    def patch(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        """
        Perform a partial update on the instance and trigger background
        processing jobs.

        This method handles the partial update of a database instance,
        deletes existing mapping rules, and triggers a series of
        background jobs to process the updated data. It ensures that no
        duplicate jobs are created for the same table while a job is
        already in progress.

        Args:
            request (Any): The HTTP request object containing the data for
                the update.
            **kwargs (Any): Additional keyword arguments. The "partial" key
                is used to determine if the update is partial (default is
                True).

        Returns:
            Response: A DRF Response object containing the serialized data
                of the updated instance or an error message if a job is
                already in progress.

        Raises:
            requests.exceptions.HTTPError: If the HTTP request to the worker
                service fails.

        Workflow:
            1. Retrieve the instance to be updated.
            2. Validate and apply the partial update using the serializer.
            3. Delete existing mapping rules for the instance.
            4. Prepare and send a message to the worker service to trigger
               background jobs.
            5. Create job records for the processing stages:
               - BUILD_CONCEPTS_FROM_DICT (initial stage, marked as
                 IN_PROGRESS)
               - REUSE_CONCEPTS
               - GENERATE_RULES
            6. Handle any HTTP errors during the worker service request.

        Notes:
            - The worker service URL and credentials are configured in the
              application settings.
            - If a job is already in progress for the table, the method
              returns a 400 BAD REQUEST response with an appropriate error
              message.
            - The worker ID returned by the worker service is not currently
              saved but can be utilized for tracking job status in the
              future.
        """
        instance: ScanReportTable = self.get_object()
        partial = kwargs.pop("partial", True)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Map the table
        scan_report_instance: ScanReport = instance.scan_report
        data_dictionary_name: Optional[str] = (
            scan_report_instance.data_dictionary.name
            if scan_report_instance.data_dictionary
            else None
        )

        # Prevent double-updating from backend
        if Job.objects.filter(
            scan_report_table=instance,
            status=StageStatus.objects.get(value="IN_PROGRESS"),
        ):
            return Response(
                {
                    "detail": "There is a job running for this table. Please wait until it complete before updating."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Trigger auto mapping
        worker_service.trigger_auto_mapping(
            scan_report=scan_report_instance,
            table=instance,
            data_dictionary_name=data_dictionary_name,
            trigger_reuse_concepts=instance.trigger_reuse,
        )

        # Create Job records if no errors
        # For the first stage, default status is IN_PROGRESS
        Job.objects.create(
            scan_report=scan_report_instance,
            scan_report_table=instance,
            stage=JobStage.objects.get(value="BUILD_CONCEPTS_FROM_DICT"),
            status=StageStatus.objects.get(value="IN_PROGRESS"),
        )
        for stage in [
            "REUSE_CONCEPTS",
            "GENERATE_RULES",
        ]:
            Job.objects.create(
                scan_report=scan_report_instance,
                scan_report_table=instance,
                stage=JobStage.objects.get(value=stage),
            )
        # TODO: The worker_id can be used for status, but we need to save it somewhere.
        # resp_json = response.json()
        # worker_id = resp_json.get("instanceId")

        return Response(serializer.data)


class ScanReportFieldIndexV2(ScanReportPermissionMixin, GenericAPIView, ListModelMixin):
    """
    A view that provides a list of ScanReportField objects associated
    with a specific ScanReportTable. This view supports filtering,
    ordering, and pagination for the ScanReportField objects. It also
    caches the response for 15 minutes and varies the cache based on
    cookies.

    Attributes:
        serializer_class (Serializer): The serializer class used for
            serializing the ScanReportField objects.
        filterset_fields (dict): Fields that can be filtered, with
            their respective lookup expressions.
        filter_backends (list): List of filter backends used for
            filtering and ordering.
        ordering_fields (list): Fields that can be used for ordering
            the results.
        pagination_class (Pagination): The pagination class used for
            paginating the results.

    Methods:
        get(request, *args, **kwargs):
            Handles GET requests and retrieves the ScanReportTable
            object based on the provided table_pk. Returns a list of
            ScanReportField objects associated with the table.
        get_queryset():
            Returns the queryset of ScanReportField objects filtered by
            the associated ScanReportTable.
        list(request, *args, **kwargs):
            Overrides the default list method to add caching and
            cookie-based variation. Returns the paginated and
            serialized list of ScanReportField objects.
    """

    serializer_class = ScanReportFieldListSerializerV2
    filterset_fields = {
        "name": ["icontains"],
    }
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["name", "description_column", "type_column"]
    pagination_class = CustomPagination

    @extend_schema(responses=ScanReportFieldListSerializerV2)
    def get(self, request, *args, **kwargs):
        self.table = get_object_or_404(ScanReportTable, pk=kwargs["table_pk"])

        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return ScanReportField.objects.filter(scan_report_table=self.table).order_by(
            "id"
        )

    @method_decorator(cache_page(60 * 15))
    @method_decorator(vary_on_cookie)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ScanReportFieldDetailV2(
    ScanReportPermissionMixin, GenericAPIView, RetrieveModelMixin, UpdateModelMixin
):
    """
    A view for handling detailed operations on ScanReportField objects.

    This view supports retrieving and partially updating a
    ScanReportField object. It uses different serializers for different
    HTTP methods and ensures proper permissions are applied through the
    ScanReportPermissionMixin.

    Inherits:
        - ScanReportPermissionMixin: Ensures the user has the required
          permissions.
        - GenericAPIView: Provides base functionality for API views.
        - RetrieveModelMixin: Adds support for retrieving a single
          model instance.
        - UpdateModelMixin: Adds support for updating a model instance.

    Attributes:
        model (Model): The model class associated with this view
            (ScanReportField).
        serializer_class (Serializer): The default serializer class for
            the view.

    Methods:
        get_object():
            Retrieves the ScanReportField object based on the
            `field_pk` URL parameter. Returns a 404 response if the
            object is not found.

        get(request, *args, **kwargs):
            Handles GET requests to retrieve a ScanReportField object.

        patch(request, *args, **kwargs):
            Handles PATCH requests to partially update a
            ScanReportField object.

        get_serializer_class():
            Determines the serializer class to use based on the HTTP
            method.
            - GET, POST: Uses ScanReportFieldListSerializerV2.
            - PUT, PATCH: Uses ScanReportFieldEditSerializer.
            Falls back to the default implementation for other methods.
    """

    model = ScanReportField
    serializer_class = ScanReportFieldListSerializerV2

    def get_object(self):
        return get_object_or_404(self.model, pk=self.kwargs["field_pk"])

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.request.method in ["GET", "POST"]:
            return ScanReportFieldListSerializerV2
        if self.request.method in ["PUT", "PATCH"]:
            return ScanReportFieldEditSerializer
        return super().get_serializer_class()


class ScanReportValueListV2(ScanReportPermissionMixin, GenericAPIView, ListModelMixin):
    """
    A view for listing ScanReportValue objects associated with a
    specific ScanReportField. This view provides filtering,
    pagination, and caching capabilities for the ScanReportValue
    objects. It uses DjangoFilterBackend for filtering and a custom
    pagination class for paginated responses. The view also caches the
    list response for 15 minutes.

    Attributes:
        filterset_fields (dict): Specifies the fields and lookup types
            available for filtering.
        filter_backends (list): Specifies the filter backends to be
            used.
        pagination_class (class): Specifies the pagination class to be
            used.
        serializer_class (class): Specifies the serializer class to be
            used for the response.

    Methods:
        get(request, *args, **kwargs):
            Handles GET requests and retrieves the ScanReportField
            object based on the provided field_pk. Returns the list of
            ScanReportValue objects associated with the field.

        get_queryset():
            Returns the queryset of ScanReportValue objects filtered by
            the associated ScanReportField. The queryset is ordered by
            ID and only includes specific fields.

        list(request, *args, **kwargs):
            Overrides the default list method to add caching and
            vary-on-cookie functionality. Returns the paginated list of
            ScanReportValue objects.
    """

    filterset_fields = {
        "value": ["in", "icontains"],
    }
    filter_backends = [DjangoFilterBackend]
    pagination_class = CustomPagination
    serializer_class = ScanReportValueViewSerializerV2

    @extend_schema(responses=ScanReportValueViewSerializerV2)
    def get(self, request, *args, **kwargs):
        self.field = get_object_or_404(ScanReportField, pk=kwargs["field_pk"])

        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return ScanReportValue.objects.filter(scan_report_field=self.field).order_by(
            "id"
        )

    @method_decorator(cache_page(60 * 15))
    @method_decorator(vary_on_cookie)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ScanReportValueListV3(ScanReportPermissionMixin, GenericAPIView, ListModelMixin):
    """
    A view for listing ScanReportValue objects associated with a
    specific ScanReportField. This view provides filtering,
    pagination, and caching capabilities for the ScanReportValue
    objects. It uses DjangoFilterBackend for filtering and a custom
    pagination class for paginated responses. The view also caches the
    list response for 15 minutes.

    Attributes:
        filterset_fields (dict): Specifies the fields and lookup types
            available for filtering.
        filter_backends (list): Specifies the filter backends to be
            used.
        pagination_class (class): Specifies the pagination class to be
            used.
        serializer_class (class): Specifies the serializer class to be
            used for the response.

    Methods:
        get(request, *args, **kwargs):
            Handles GET requests and retrieves the ScanReportField
            object based on the provided field_pk. Returns the list of
            ScanReportValue objects associated with the field.

        get_queryset():
            Returns the queryset of ScanReportValue objects filtered by
            the associated ScanReportField. The queryset is ordered by
            ID and only includes specific fields.

        list(request, *args, **kwargs):
            Overrides the default list method to add caching and
            vary-on-cookie functionality. Returns the paginated list of
            ScanReportValue objects.
    """

    filterset_class = ScanReportValueFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["value", "frequency", "value_description"]
    pagination_class = CustomPagination
    serializer_class = ScanReportValueViewSerializerV3

    @extend_schema(responses=ScanReportValueViewSerializerV3)
    def get(self, request, *args, **kwargs):
        self.field = get_object_or_404(ScanReportField, pk=kwargs["field_pk"])

        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return (
            ScanReportValue.objects.filter(scan_report_field=self.field)
            .order_by("id")
            .select_related("scan_report_field")
            .prefetch_related(
                "concepts",
                "concepts__concept",
                "mapping_recommendations",
                "mapping_recommendations__concept",
            )
        )

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ScanReportConceptDetailV3(
    ScanReportPermissionMixin, GenericAPIView, RetrieveModelMixin, UpdateModelMixin
):
    """
    A view for retrieving a specific ScanReportConcept object.
    """

    serializer_class = ScanReportConceptDetailSerializerV3

    def get_object(self):
        return get_object_or_404(ScanReportConcept, pk=self.kwargs["concept_pk"])

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class ScanReportConceptListV2(
    GenericAPIView, ListModelMixin, CreateModelMixin, DestroyModelMixin
):
    """
    API view for managing ScanReportConcept objects (Version V2).

    This view provides functionality to list, create, and delete
    ScanReportConcept objects. It includes validation logic for
    ensuring data integrity and consistency when creating new
    ScanReportConcept entries.

    Attributes:
        queryset (QuerySet): Queryset for retrieving all
            ScanReportConcept objects, ordered by their ID.
        serializer_class (Serializer): Serializer class used for
            ScanReportConcept objects.
        pagination_class (Pagination): Custom pagination class for
            paginating results.
        filter_backends (list): List of filter backends used for
            filtering query results.
        filterset_fields (dict): Dictionary defining the fields that
            can be filtered and the filtering operations allowed.

    Methods:
        get(request, *args, **kwargs):
            Handles GET requests to retrieve a list of
            ScanReportConcept objects.

        post(request, *args, **kwargs):
            Handles POST requests to create a new ScanReportConcept
            object. Includes validation for:
                - Ensuring the associated table exists and has
                  `person_id` and `date_event` set.
                - Ensuring the referenced concept exists in the
                  database.
                - Validating the data type of the field for concepts
                  with the "Observation" domain.
                - Ensuring the destination table for the concept is
                  valid.
                - Preventing multiple concepts with the same ID from
                  being added to the same object.
            Returns appropriate error responses for validation
            failures.

    GenericAPIView, ListModelMixin, CreateModelMixin,
    DestroyModelMixin
    """

    queryset = ScanReportConcept.objects.all().order_by("id")
    serializer_class = ScanReportConceptSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        "concept__concept_id": ["in", "exact"],
        "object_id": ["in", "exact"],
        "id": ["in", "exact"],
        "content_type": ["in", "exact"],
    }

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        body = request.data

        # Extract the content_type
        content_type_str = body.pop("content_type", None)
        content_type = ContentType.objects.get(model=content_type_str)
        body["content_type"] = content_type.id

        # validate person_id and date event are set on table
        table_id = body.pop("table_id", None)
        try:
            table = ScanReportTable.objects.get(pk=table_id)
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Table with the provided ID does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not table.person_id and not table.date_event:
            return Response(
                {"detail": "Please set both person_id and date_event on the table."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif not table.person_id:
            return Response(
                {"detail": "Please set the person_id on the table."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif not table.date_event:
            return Response(
                {"detail": "Please set the date_event on the table."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # validate that the concept exists.
        concept_id = body.get("concept", None)
        try:
            concept = Concept.objects.get(pk=concept_id)
        except ObjectDoesNotExist:
            return Response(
                {"detail": f"Concept id {concept_id} does not exist in our database."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get the domain and data type of the field for the check below
        domain = concept.domain_id.lower()
        # If users add the concept at "SR_Field" level
        try:
            field_datatype = ScanReportField.objects.get(
                pk=body["object_id"]
            ).type_column
        # If users add the concept at "SR_Value" level
        except:
            field_datatype = ScanReportValue.objects.get(
                pk=body["object_id"]
            ).scan_report_field.type_column

        # Checking field's datatype for concept with domain Observation
        if domain == "observation" and field_datatype.lower() not in [
            "real",
            "int",
            "tinyint",
            "smallint",
            "bigint",
            "varchar",
            "nvarchar",
            "float",
        ]:
            return Response(
                {
                    "detail": "Concept having 'Observation' domain should be only added to fields having REAL, INT, FLOAT, NVARCHAR or VARCHAR data type."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # validate the destination_table
        destination_table = _find_destination_table(concept)
        if destination_table is None:
            return Response(
                {
                    "detail": "The destination table could not be found or has not been implemented."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate that multiple concepts are not being added.
        sr_concept = ScanReportConcept.objects.filter(
            concept=body["concept"],
            object_id=body["object_id"],
            content_type=content_type,
        )
        if sr_concept.count() > 0:
            return Response(
                {
                    "detail": "Can't add multiple concepts of the same id to the same object"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Create serializer and validate
        serializer = self.get_serializer(data=body, many=isinstance(body, list))
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        model = serializer.instance
        rules = save_mapping_rules(model)
        if not rules:
            return Response(
                {"detail": "Rule could not be saved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer):
        """
        Override perform_create to set the created_by field to the current user.
        """
        serializer.save(
            created_by=self.request.user,
            mapping_tool="carrot-mapper",
            mapping_tool_version=version("api"),
        )


class ScanReportConceptDetailV2(GenericAPIView, DestroyModelMixin):
    """
    A view for handling detailed operations on ScanReportConcept objects.

    This view provides functionality for retrieving and deleting
    individual ScanReportConcept instances.

    Attributes:
        model (Model): The model associated with this view, which is
            ScanReportConcept.
        queryset (QuerySet): The queryset used to retrieve
            ScanReportConcept objects.
        serializer_class (Serializer): The serializer class used for
            serializing and deserializing ScanReportConcept objects.

    Methods:
        delete(request, *args, **kwargs):
            Handles DELETE requests to delete a specific
            ScanReportConcept instance. Delegates the deletion logic
            to the `destroy` method provided by DestroyModelMixin.
    """

    model = ScanReportConcept
    queryset = ScanReportConcept.objects.all()
    serializer_class = ScanReportConceptSerializer

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class MappingRulesList(APIView):
    """
    API View to handle operations related to mapping rules.

    This view provides functionality to retrieve mapping rules in a
    specific format or generate an SVG representation of the mapping
    rules DAG (Directed Acyclic Graph).

    Methods:
        post(request, *args, **kwargs):
            Handles POST requests to either retrieve mapping rules in
            JSON format or generate an SVG representation of the
            mapping rules DAG.

            Request Parameters:
                - get_svg (optional, boolean): If provided and set to
                  true, the response will include an SVG representation
                  of the mapping rules DAG.

            Request Body (JSON):
                - get_svg (optional, boolean): Same as the request
                  parameter.

            Responses:
                - 200 OK: Returns an SVG image if `get_svg` is provided.
                - 400 Bad Request: Returns an error message if the
                  request parameters are invalid.

        get_queryset():
            Retrieves the queryset of mapping rules based on the
            provided search term.

            Query Parameters:
                - pk (optional, integer): The primary key of the scan
                  report to filter mapping rules by. If not provided,
                  all mapping rules are returned.

            Returns:
                - QuerySet: A filtered queryset of MappingRule objects
                  ordered by concept, OMOP table, OMOP field, source
                  table, and source field.
    """

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="get_svg",
                type=OpenApiTypes.BOOL,
                description="Set to true to get an SVG of the mapping rules DAG.",
            )
        ],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request, *args, **kwargs):
        try:
            body = request.data
        except ValueError:
            body = {}
        if request.POST.get("get_svg") is not None or body.get("get_svg") is not None:
            qs = self.get_queryset()
            output = get_mapping_rules_json(qs)

            # use make dag svg image
            svg = make_dag(output["cdm"])
            return HttpResponse(svg, content_type="image/svg+xml")
        else:
            return Response(
                {"error": "Invalid request parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get_queryset(self):
        qs = MappingRule.objects.all()
        search_term = self.kwargs.get("pk")

        if search_term is not None:
            qs = qs.filter(scan_report__id=search_term).order_by(
                "concept",
                "omop_field__table",
                "omop_field__field",
                "source_field__name",
            )

        return qs


class RulesListV2(ScanReportPermissionMixin, GenericAPIView, ListModelMixin):
    """
    A view that provides a paginated list of MappingRule objects
    filtered by the ID of a related ScanReport. This view does not
    use a serializer class directly but instead processes the
    queryset and pagination manually.

    Attributes:
        queryset (QuerySet): The base queryset for MappingRule objects,
            ordered by ID.
        pagination_class (CustomPagination): The pagination class used
            for paginating results.
        filter_backends (list): A list of filter backends applied to
            the queryset.
        http_method_names (list): Allowed HTTP methods for this view.

    Methods:
        get_queryset():
            Retrieves the queryset filtered by the ScanReport ID
            provided in the URL kwargs.
        get(request, *args, **kwargs):
            Handles GET requests and returns a paginated list of
            MappingRule objects.
        list(request, *args, **kwargs):
            Custom implementation of the list method to handle
            pagination and filtering manually. Processes MappingRule
            objects to include additional details about related
            fields (e.g., destination_table, source_field).
    """

    queryset = MappingRule.objects.all().order_by("id")
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    http_method_names = ["get"]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="p",
                type=OpenApiTypes.INT,
                description="Page number for pagination.",
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                description="Number of items per page.",
            ),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get_queryset(self):
        _id = self.kwargs["pk"]
        queryset = self.queryset
        if _id is not None:
            queryset = queryset.filter(scan_report__id=_id)
        return queryset

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """
        This is a somewhat strange way of doing things (because we don't use a serializer class,
        but seems to be a limitation of how django handles the combination of pagination and
        filtering on ID of a model (ScanReport) that's not that being returned (MappingRule).

        Instead, this is in effect a ListSerializer for MappingRule but that only works for in
        the scenario we have. This means that get_mapping_rules_list() must now handle pagination
        directly.
        """
        queryset = self.queryset
        _id = self.kwargs["pk"]
        # Filter on ScanReport ID
        if _id is not None:
            queryset = queryset.filter(scan_report__id=_id)
        count = queryset.count()

        # Get subset of mapping rules that fit onto the page to be displayed
        p = self.request.query_params.get("p", 1)
        page_size = self.request.query_params.get("page_size", 30)
        rules = get_mapping_rules_list(
            queryset, page_number=int(p), page_size=int(page_size)
        )

        # Process all rules
        for rule in rules:
            rule["destination_table"] = {
                "id": int(str(rule["destination_table"])),
                "name": rule["destination_table"].table,
            }

            rule["destination_field"] = {
                "id": int(str(rule["destination_field"])),
                "name": rule["destination_field"].field,
            }

            rule["domain"] = {
                "name": rule["domain"],
            }

            rule["source_table"] = {
                "id": int(str(rule["source_table"])),
                "name": rule["source_table"].name,
            }

            rule["source_field"] = {
                "id": int(str(rule["source_field"])),
                "name": rule["source_field"].name,
            }

        return Response(data={"count": count, "results": rules})


class SummaryRulesListV2(RulesListV2):
    """
    A view that provides a paginated list of MappingRule objects
    filtered by the ID of a related ScanReport.
    This view does not use a serializer class directly but instead
    processes the queryset and pagination manually.

    Attributes:
        queryset (QuerySet): The base queryset for MappingRule objects,
            ordered by ID.
        pagination_class (CustomPagination): The pagination class used for
            paginating results.
        filter_backends (list): A list of filter backends applied to the
            queryset.
        http_method_names (list): Allowed HTTP methods for this view.

    Methods:
        get_queryset():
            Retrieves the queryset filtered by the ScanReport ID provided
            in the URL kwargs.
        get(request, *args, **kwargs):
            Handles GET requests and returns a paginated list of
            MappingRule objects.
        list(request, *args, **kwargs):
            Custom implementation of the list method to handle pagination
            and filtering manually. Processes MappingRule objects to
            include additional details about related fields (e.g.,
            destination_table, source_field).
    """

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="p",
                type=OpenApiTypes.INT,
                description="Page number for pagination.",
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                description="Number of items per page.",
            ),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def list(self, request, *args, **kwargs):
        # Get p and page_size from query_params
        p = self.request.query_params.get("p", 1)
        page_size = self.request.query_params.get("page_size", 20)
        # Get queryset
        queryset = self.get_queryset()

        # Directly filter OmopField objects that end with "_concept_id" but not "_source_concept_id"
        omop_fields_queryset = OmopField.objects.filter(
            pk__in=queryset.values_list("omop_field_id", flat=True),
            field__endswith="_concept_id",
        ).exclude(
            Q(field__endswith="_source_concept_id")
            | Q(field__endswith="value_as_concept_id")
        )

        ids_list = omop_fields_queryset.values_list("id", flat=True)
        # Filter the queryset based on valid omop_field_ids
        filtered_queryset = queryset.filter(omop_field_id__in=ids_list)
        count = filtered_queryset.count()
        # Get the rules list based on the filtered queryset
        rules = get_mapping_rules_list(
            filtered_queryset, page_number=int(p), page_size=int(page_size)
        )
        # Process rules
        for rule in rules:
            rule["destination_table"] = {
                "id": int(str(rule["destination_table"])),
                "name": rule["destination_table"].table,
            }

            rule["destination_field"] = {
                "id": int(str(rule["destination_field"])),
                "name": rule["destination_field"].field,
            }

            rule["domain"] = {
                "name": rule["domain"],
            }

            rule["source_table"] = {
                "id": int(str(rule["source_table"])),
                "name": rule["source_table"].name,
            }

            rule["source_field"] = {
                "id": int(str(rule["source_field"])),
                "name": rule["source_field"].name,
            }

        return Response(data={"count": count, "results": rules})


class AnalyseRulesV2(ScanReportPermissionMixin, GenericAPIView, RetrieveModelMixin):
    """
    A view for retrieving the analysis of rules for a specific
    scan report. This view allows users to obtain detailed
    information about the rules associated with a scan report,
    including their status and other relevant details.

    Attributes:
        queryset (QuerySet): The base queryset for ScanReport objects.
        serializer_class (Serializer): The serializer class used for
            serializing the response.
        filter_backends (list): A list of filter backends applied to
            the queryset.
        filterset_fields (dict): A dictionary defining the fields that
            can be filtered.
    """

    queryset = ScanReport.objects.all()
    serializer_class = GetRulesAnalysis
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["id"]


class DownloadScanReportViewSet(viewsets.ViewSet):
    """
    A ViewSet for handling the download of scan reports.
    Methods:
        list(request, pk):
            Handles the retrieval and download of a specific scan report
            based on its primary key (pk). This method is not intended to
            behave as a typical list view.
    Methods Details:
        list(request, pk):
            Args:
                request (HttpRequest): The HTTP request object.
                pk (int): The primary key of the scan report to be downloaded.
            Returns:
                HttpResponse: A response containing the scan report file as an
                attachment with the appropriate content type and disposition.
            Raises:
                ScanReport.DoesNotExist: If no scan report is found with the given primary key.
    """

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={
            200: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Download a specific scan report.",
    )
    def list(self, request, pk):
        # TODO: This should not be a list view...
        scan_report = ScanReport.objects.get(id=pk)
        blob_name = scan_report.name
        scan_report_blob = storage_service.get_file(blob_name, "scan-reports")

        response = HttpResponse(
            scan_report_blob,
            content_type="application/octet-stream",
        )
        response["Content-Disposition"] = f'attachment; filename="{blob_name}"'

        return response


class ScanReportPermissionView(APIView):
    """
    Handles API requests to retrieve the permissions a user has on a
    specific scan report.

    Methods:
        get(request, pk):
            Retrieves the permissions for the user on the scan report
            identified by the given primary key (pk).

    Args:
        request (Request): The HTTP request object containing user and
            request data.
        pk (int): The primary key of the scan report for which
            permissions are being retrieved.

    Returns:
        Response: A JSON response containing the user's permissions on
            the scan report, with an HTTP status code of 200 (OK).
    """

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={
            200: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        description="Retrieve user permissions on a specific scan report.",
    )
    def get(self, request, pk):
        permissions = get_user_permissions_on_scan_report(request, pk)

        return Response({"permissions": permissions}, status=status.HTTP_200_OK)


class HealthCheckView(APIView):
    """
    A simple health check endpoint that returns 200 OK.
    This endpoint is used by Docker health checks to verify the service is running.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {"status": "healthy", "version": version("api")}, status=status.HTTP_200_OK
        )

import datetime
import logging
import os
import random
import string
from typing import Any
from urllib.parse import urljoin

import requests
from api.filters import ScanReportAccessFilter
from api.mixins import ScanReportPermissionMixin
from api.paginations import CustomPagination
from api.serializers import (
    ConceptSerializerV2,
    GetRulesAnalysis,
    ScanReportConceptSerializer,
    ScanReportCreateSerializer,
    ScanReportEditSerializer,
    ScanReportFieldEditSerializer,
    ScanReportFieldListSerializerV2,
    ScanReportFilesSerializer,
    ScanReportTableEditSerializer,
    ScanReportTableListSerializerV2,
    ScanReportValueViewSerializerV2,
    ScanReportViewSerializerV2,
    UserSerializer,
)
from azure.storage.blob import BlobServiceClient
from config import settings
from datasets.serializers import DataPartnerSerializer
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django_filters.rest_framework import DjangoFilterBackend
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
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from shared.data.models import Concept
from shared.files.service import delete_blob, modify_filename, upload_blob
from shared.mapping.models import (
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
from shared.mapping.permissions import get_user_permissions_on_scan_report
from shared.services.azurequeue import add_message
from shared.services.rules import (
    _find_destination_table,
    _save_mapping_rules,
    delete_mapping_rules,
)
from shared.services.rules_export import (
    get_mapping_rules_json,
    get_mapping_rules_list,
    make_dag,
)
from django.db.models import Q


class DataPartnerViewSet(GenericAPIView, ListModelMixin):
    queryset = DataPartner.objects.all()
    serializer_class = DataPartnerSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class ConceptFilterViewSetV2(GenericAPIView, ListModelMixin):
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
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class UserFilterViewSet(GenericAPIView, ListModelMixin):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {"id": ["in", "exact"], "is_active": ["exact"]}

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class ScanReportIndexV2(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    A custom viewset for retrieving and listing scan reports with additional functionality for version 2.

    Remarks:
    - This viewset extends ScanReportListViewSet and provides custom behavior listing scan reports.
    - Includes custom filtering, ordering, and pagination.
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
            name=modify_filename(valid_scan_report_file, dt, rand),
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

        # If there's no data dictionary supplied, only upload the scan report
        # Set data_dictionary_blob in Azure message to None
        if str(valid_data_dictionary_file) == "None":
            azure_dict = {
                "scan_report_id": scan_report.id,
                "scan_report_blob": scan_report.name,
                "data_dictionary_blob": "None",
            }

            upload_blob(
                scan_report.name,
                "scan-reports",
                valid_scan_report_file,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        else:
            data_dictionary = DataDictionary.objects.create(
                name=f"{os.path.splitext(str(valid_data_dictionary_file))[0]}"
                f"_{dt}{rand}.csv"
            )
            data_dictionary.save()
            scan_report.data_dictionary = data_dictionary
            scan_report.save()

            azure_dict = {
                "scan_report_id": scan_report.id,
                "scan_report_blob": scan_report.name,
                "data_dictionary_blob": data_dictionary.name,
            }

            upload_blob(
                scan_report.name,
                "scan-reports",
                valid_scan_report_file,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            upload_blob(
                data_dictionary.name,
                "data-dictionaries",
                valid_data_dictionary_file,
                "text/csv",
            )

        # send to the upload queue
        add_message(os.environ.get("UPLOAD_QUEUE_NAME"), azure_dict)


class ScanReportDetailV2(
    ScanReportPermissionMixin,
    GenericAPIView,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
):
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
            delete_blob(instance.name, "scan-reports")
        except Exception as e:
            raise Exception(f"Error deleting scan report: {e}")
        if instance.data_dictionary:
            try:
                delete_blob(instance.data_dictionary.name, "data-dictionaries")
            except Exception as e:
                raise Exception(f"Error deleting data dictionary: {e}")
        instance.delete()


class ScanReportTableIndexV2(ScanReportPermissionMixin, GenericAPIView, ListModelMixin):
    """
    A paginated list of Scan Report Tables, for a specific Scan Report.

    Allows ordering by name, person_id, and date_event
    Allows filtering by name.
    """

    filterset_fields = {
        "name": ["icontains"],
    }
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["name", "person_id", "date_event"]
    pagination_class = CustomPagination
    ordering = "-created_at"
    serializer_class = ScanReportTableListSerializerV2

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return ScanReportTable.objects.filter(scan_report=self.scan_report)


class ScanReportTableDetailV2(
    ScanReportPermissionMixin, GenericAPIView, RetrieveModelMixin, UpdateModelMixin
):
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
        Perform a partial update on the instance.

        Args:
            request (Any): The request object.
            *args (Any): Additional positional arguments.
            **kwargs (Any): Additional keyword arguments.

        Returns:
            Response: The response object.
        """
        instance = self.get_object()
        partial = kwargs.pop("partial", True)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Delete the current mapping rules
        delete_mapping_rules(instance.id)

        # Map the table
        scan_report_instance = instance.scan_report
        data_dictionary_name = (
            scan_report_instance.data_dictionary.name
            if scan_report_instance.data_dictionary
            else None
        )

        # Send to functions
        msg = {
            "scan_report_id": scan_report_instance.id,
            "table_id": instance.id,
            "data_dictionary_blob": data_dictionary_name,
        }
        base_url = f"{settings.AZ_URL}"
        trigger = (
            f"/api/orchestrators/{settings.AZ_RULES_NAME}?code={settings.AZ_RULES_KEY}"
        )
        try:
            response = requests.post(urljoin(base_url, trigger), json=msg)
            response.raise_for_status()
        except request.exceptions.HTTPError as e:
            logging.error(f"HTTP Trigger failed: {e}")

        # TODO: The worker_id can be used for status, but we need to save it somewhere.
        # resp_json = response.json()
        # worker_id = resp_json.get("instanceId")

        return Response(serializer.data)


class ScanReportFieldIndexV2(ScanReportPermissionMixin, GenericAPIView, ListModelMixin):
    serializer_class = ScanReportFieldListSerializerV2
    filterset_fields = {
        "name": ["icontains"],
    }
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["name", "description_column", "type_column"]
    pagination_class = CustomPagination

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
    filterset_fields = {
        "value": ["in", "icontains"],
    }
    filter_backends = [DjangoFilterBackend]
    pagination_class = CustomPagination
    serializer_class = ScanReportValueViewSerializerV2

    def get(self, request, *args, **kwargs):
        self.field = get_object_or_404(ScanReportField, pk=kwargs["field_pk"])

        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return (
            ScanReportValue.objects.filter(scan_report_field=self.field)
            .order_by("id")
            .only("id", "value", "frequency", "value_description", "scan_report_field")
        )

    @method_decorator(cache_page(60 * 15))
    @method_decorator(vary_on_cookie)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ScanReportConceptListV2(
    GenericAPIView, ListModelMixin, CreateModelMixin, DestroyModelMixin
):
    """
    Version V2.
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

        # Checking death_table and meas value domain relationship
        if domain == "meas value" and table.death_table:
            return Response(
                {
                    "detail": "Because concepts with 'Meas Value' domain will be mapped to Measurement table as 'value_as_concept_id', they should not be added to DEATH table."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Checking field's datatype for concept with domain Observation
        if domain == "observation" and field_datatype.lower() not in [
            "real",
            "int",
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
        destination_table = _find_destination_table(concept, table)
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

        serializer = self.get_serializer(data=body, many=isinstance(body, list))
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        model = serializer.instance
        saved = _save_mapping_rules(model)
        if not saved:
            return Response(
                {"detail": "Rule could not be saved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class ScanReportConceptDetailV2(GenericAPIView, DestroyModelMixin):
    model = ScanReportConcept
    queryset = ScanReportConcept.objects.all()
    serializer_class = ScanReportConceptSerializer

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class MappingRulesList(APIView):
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
                "source_table__name",
                "source_field__name",
            )

        return qs


class RulesListV2(ScanReportPermissionMixin, GenericAPIView, ListModelMixin):
    queryset = MappingRule.objects.all().order_by("id")
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    http_method_names = ["get"]

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
    queryset = ScanReport.objects.all()
    serializer_class = GetRulesAnalysis
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["id"]


class DownloadScanReportViewSet(viewsets.ViewSet):
    def list(self, request, pk):
        # TODO: This should not be a list view...
        scan_report = ScanReport.objects.get(id=pk)
        # scan_report = ScanReportSerializer(scan_reports, many=False).data
        # Set Storage Account connection string
        print(scan_report)
        # TODO: `name` is not always defined, it seems
        blob_name = scan_report.name
        print(blob_name)
        container = "scan-reports"
        blob_service_client = BlobServiceClient.from_connection_string(
            os.environ.get("STORAGE_CONN_STRING")
        )

        # Grab scan report data from blob
        streamdownloader = (
            blob_service_client.get_container_client(container)
            .get_blob_client(blob_name)
            .download_blob()
        )
        scan_report = streamdownloader.readall()

        response = HttpResponse(
            scan_report,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{blob_name}"'

        return response


class ScanReportPermissionView(APIView):
    """
    API for permissions a user has on a specific scan report.
    """

    def get(self, request, pk):
        permissions = get_user_permissions_on_scan_report(request, pk)

        return Response({"permissions": permissions}, status=status.HTTP_200_OK)

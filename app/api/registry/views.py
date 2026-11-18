import logging
from importlib.metadata import version

from api.mixins import ScanReportPermissionMixin
from api.paginations import CustomPagination
from django.conf import settings
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from mapping.models import ScanReport
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from services.storage_service import StorageService

from registry.download_helpers import StorageUnavailable, sssom_download_filename
from registry.filters import (
    ImportJobFilter,
    MappingFilter,
    MappingSetFilter,
    RelevanceOrderingFilter,
    TermFilter,
)
from registry.models import (
    ImportJob,
    License,
    Mapping,
    MappingJustification,
    Predicate,
)
from registry.permissions import (
    IsPublisherOrRegistryAdmin,
    published_mappings,
    published_terms,
    visible_import_jobs,
    visible_mapping_sets,
)
from registry.serializers import (
    ImportJobSerializer,
    LicenseSerializer,
    MappingJustificationSerializer,
    MappingSerializer,
    MappingSetDetailSerializer,
    MappingSetListSerializer,
    MappingSetWithdrawSerializer,
    PredicateSerializer,
    RegistryImportAcceptedSerializer,
    ScanReportRegistryPublishSerializer,
    TermSerializer,
)
from registry.services import (
    publish_mapping_set,
    submit_direct_publish,
    withdraw_mapping_set,
)

logger = logging.getLogger(__name__)

storage_service = StorageService()

# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


class ScanReportRegistryPublishView(ScanReportPermissionMixin, GenericAPIView):
    """
    Publish a scan report's mappings to the Carrot Mappings Registry.

    Requires edit or admin rights on the scan report. The import runs
    asynchronously: the response carries the ImportJob id to poll.
    """

    queryset = ScanReport.objects.all()
    serializer_class = ScanReportRegistryPublishSerializer
    http_method_names = ["post"]

    @extend_schema(
        request=ScanReportRegistryPublishSerializer,
        responses={202: RegistryImportAcceptedSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job, _ = submit_direct_publish(
            scan_report=self.scan_report,
            user=request.user,
            metadata=serializer.validated_data,
            mapper_version=version("api"),
        )

        return Response(
            RegistryImportAcceptedSerializer(
                {"import_job_id": job.id, "status": job.status}
            ).data,
            status=status.HTTP_202_ACCEPTED,
        )


class ImportJobListView(ListAPIView):
    """The caller's own registry imports, newest first."""

    serializer_class = ImportJobSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ImportJobFilter

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ImportJob.objects.none()
        return ImportJob.objects.filter(
            submitted_by=self.request.user
        ).prefetch_related("mapping_sets")


class ImportJobDetailView(RetrieveAPIView):
    """
    One registry import, for polling after a publish.

    Visible to its submitter and to registry admins. `mapping_set` is set once
    the import has succeeded.
    """

    serializer_class = ImportJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return visible_import_jobs(self.request.user).prefetch_related("mapping_sets")


class MappingSetStatusView(GenericAPIView):
    """Base for the endpoints that move a mapping set through its lifecycle."""

    serializer_class = MappingSetDetailSerializer
    permission_classes = [IsAuthenticated, IsPublisherOrRegistryAdmin]
    http_method_names = ["post"]

    def get_queryset(self):
        return mapping_set_detail_queryset(self.request.user)

    def updated_response(self) -> Response:
        return Response(
            self.get_serializer(self.get_queryset().get(pk=self.kwargs["pk"])).data
        )


class MappingSetPublishView(MappingSetStatusView):
    """Publish a draft mapping set. For its publisher and registry admins."""

    @extend_schema(
        request=None,
        responses={
            200: MappingSetDetailSerializer,
            409: OpenApiResponse(
                description="Not a draft, or its import has not finished."
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        mapping_set = self.get_object()
        publish_mapping_set(mapping_set.pk, request.user)
        return self.updated_response()


class MappingSetWithdrawView(MappingSetStatusView):
    """
    Withdraw a published mapping set. For its publisher and registry admins.

    The set stays available by id and for download, with the reason given, but
    leaves default listings and search. Sets are never deleted.
    """

    @extend_schema(
        request=MappingSetWithdrawSerializer,
        responses={
            200: MappingSetDetailSerializer,
            409: OpenApiResponse(
                description="Not published, or its import has not finished."
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        mapping_set = self.get_object()
        serializer = MappingSetWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        withdraw_mapping_set(
            mapping_set.pk, request.user, serializer.validated_data["reason"]
        )
        return self.updated_response()


# ---------------------------------------------------------------------------
# Read: discovery, search, filter
#
# Reads are public; visibility by set status is defined in
# registry/permissions.py.
# ---------------------------------------------------------------------------


def _count_mappings(field: str = "pk", distinct: bool = False) -> Coalesce:
    """Correlated COUNT over a set's mappings (avoids GROUP BY on the outer query)."""
    counts = (
        Mapping.objects.filter(mapping_set=OuterRef("pk"))
        .order_by()
        .values("mapping_set")
        .annotate(n=Count(field, distinct=distinct))
        .values("n")
    )
    return Coalesce(Subquery(counts, output_field=IntegerField()), 0)


def mapping_set_detail_queryset(user):
    return (
        visible_mapping_sets(user)
        .select_related("import_job")
        .annotate(
            mapping_count=_count_mappings(),
            subject_count=_count_mappings("subject", distinct=True),
            object_count=_count_mappings("object", distinct=True),
        )
    )


class PublicReadMixin:
    permission_classes = [AllowAny]


class MappingSetListView(PublicReadMixin, ListAPIView):
    """
    List and search mapping sets.

    Only PUBLISHED sets are listed unless `status` is given. With `q`, results
    are ordered by relevance (exact set_uri, then title prefix, then fuzzy
    match) unless `ordering` is given.
    """

    serializer_class = MappingSetListSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, RelevanceOrderingFilter]
    filterset_class = MappingSetFilter
    ordering_fields = [
        "title",
        "set_version",
        "created_at",
        "published_at",
        "publication_date",
        "mapping_count",
    ]
    ordering = ["-published_at", "-created_at"]

    def get_queryset(self):
        return visible_mapping_sets(self.request.user).annotate(
            mapping_count=_count_mappings()
        )


class MappingSetDetailView(PublicReadMixin, RetrieveAPIView):
    """Mapping set metadata, curie_map, counts and import provenance."""

    serializer_class = MappingSetDetailSerializer

    def get_queryset(self):
        return mapping_set_detail_queryset(self.request.user)


class MappingSetDownloadView(PublicReadMixin, GenericAPIView):
    """
    Download a mapping set's SSSOM file.

    Streams the stored file (the uploaded original, or the file built by a
    direct publish) unchanged, so the download is lossless. Same visibility
    as the set itself: PUBLISHED and WITHDRAWN for everyone, DRAFT for the
    submitter and registry admins.
    """

    def get_queryset(self):
        return visible_mapping_sets(self.request.user)

    @extend_schema(
        responses={
            (200, "text/tab-separated-values"): OpenApiResponse(
                response=OpenApiTypes.BINARY, description="The SSSOM TSV file."
            ),
            404: OpenApiResponse(description="Set not found or has no file."),
            503: OpenApiResponse(description="Storage unavailable."),
        }
    )
    def get(self, request, *args, **kwargs):
        mapping_set = self.get_object()
        if not mapping_set.file_key:
            raise NotFound("This mapping set has no SSSOM file.")

        try:
            content = storage_service.get_file(
                mapping_set.file_key, settings.REGISTRY_SSSOM_CONTAINER
            )
        except Exception as e:
            logger.exception(
                "Failed to read SSSOM file %s for mapping set %s",
                mapping_set.file_key,
                mapping_set.pk,
            )
            raise StorageUnavailable() from e

        response = HttpResponse(
            content, content_type="text/tab-separated-values; charset=utf-8"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{sssom_download_filename(mapping_set)}"'
        )
        return response


class MappingQuerysetMixin:
    serializer_class = MappingSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, RelevanceOrderingFilter]
    filterset_class = MappingFilter
    ordering_fields = ["id", "confidence", "mapping_date"]
    ordering = ["id"]

    @staticmethod
    def with_related(qs):
        return qs.select_related("subject", "object", "mapping_set")


class MappingListView(PublicReadMixin, MappingQuerysetMixin, ListAPIView):
    """
    Cross-set mapping search over PUBLISHED mapping sets.

    `q` fuzzy-matches subject and object labels and CURIEs; `subject_id` and
    `object_id` match a CURIE exactly. Check `predicate_modifier`: "Not"
    negates the mapping.
    """

    def get_queryset(self):
        return self.with_related(published_mappings())


class MappingSetMappingsView(PublicReadMixin, MappingQuerysetMixin, ListAPIView):
    """Mappings inside one mapping set (any status the caller may see)."""

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Mapping.objects.none()
        mapping_set = get_object_or_404(
            visible_mapping_sets(self.request.user), pk=self.kwargs["pk"]
        )
        return self.with_related(Mapping.objects.filter(mapping_set=mapping_set))


class TermListView(PublicReadMixin, ListAPIView):
    """
    Term search and autocomplete, over terms used in PUBLISHED mapping sets.

    With `q`, results are ordered by relevance (exact CURIE, then prefix, then
    fuzzy match) unless `ordering` is given.
    """

    serializer_class = TermSerializer
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, RelevanceOrderingFilter]
    filterset_class = TermFilter
    ordering_fields = ["canonical_iri", "label"]
    ordering = ["canonical_iri"]

    def get_queryset(self):
        return published_terms()


class TermDetailView(PublicReadMixin, RetrieveAPIView):
    serializer_class = TermSerializer

    def get_queryset(self):
        return published_terms()


class TermMappingsView(PublicReadMixin, MappingQuerysetMixin, ListAPIView):
    """Every published mapping where the term is the subject or the object."""

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Mapping.objects.none()
        term = get_object_or_404(published_terms(), pk=self.kwargs["pk"])
        return self.with_related(
            published_mappings().filter(Q(subject=term) | Q(object=term))
        )


class PredicateListView(PublicReadMixin, ListAPIView):
    """SSSOM predicates accepted by the registry (unpaginated)."""

    serializer_class = PredicateSerializer
    queryset = Predicate.objects.order_by("-is_recommended", "predicate_id")


class MappingJustificationListView(PublicReadMixin, ListAPIView):
    """SEMAPV mapping justifications accepted by the registry (unpaginated)."""

    serializer_class = MappingJustificationSerializer
    queryset = MappingJustification.objects.order_by("justification_id")


class LicenseListView(ListAPIView):
    """
    List all registry licences for authenticated
    users.

    Note: Consider using Pagination for large
    sets of licences in the future.
    """

    queryset = License.objects.filter(is_deprecated=False).order_by("label", "id")
    serializer_class = LicenseSerializer
    pagination_class = None

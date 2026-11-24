from django.contrib.postgres.fields import ArrayField
from django.db.models import F, Func, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Cast
from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter

from registry.models import (
    Mapping,
    MappingSet,
    PredicateModifier,
    Status,
    Term,
    TermKind,
    TermLevel,
)
from registry.search import order_by_relevance, search_mapping_sets, search_terms


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    """Comma-separated list, e.g. ``?status=PUBLISHED,WITHDRAWN``."""


class UUIDInFilter(filters.BaseInFilter, filters.UUIDFilter):
    pass


class MappingSetFilter(filters.FilterSet):
    q = filters.CharFilter(
        method="filter_q",
        help_text="Fuzzy search over title and description; exact match on set_uri.",
    )
    status = CharInFilter(
        field_name="status_id",
        help_text="Comma-separated statuses. Defaults to PUBLISHED.",
    )
    origin = CharInFilter(field_name="origin_id")
    license = CharInFilter(field_name="license_id")
    set_uri = filters.CharFilter(field_name="series__set_uri")
    series = UUIDInFilter(field_name="series_id")
    subject_source = filters.CharFilter(
        field_name="subject_source", lookup_expr="iexact"
    )
    object_source = filters.CharFilter(field_name="object_source", lookup_expr="iexact")
    object_source_version = filters.CharFilter(field_name="object_source_version")
    creator_id = filters.CharFilter(
        method="filter_creator_id", help_text="CURIE in creator_ids, e.g. an ORCID."
    )
    published_after = filters.DateFilter(
        field_name="published_at", lookup_expr="date__gte"
    )
    published_before = filters.DateFilter(
        field_name="published_at", lookup_expr="date__lte"
    )
    latest = filters.BooleanFilter(
        method="filter_latest",
        help_text="Only the highest version of each set_uri (among the matching statuses).",
    )

    class Meta:
        model = MappingSet
        fields: list[str] = []

    def filter_queryset(self, queryset):
        # Default listings show PUBLISHED only; withdrawn and draft sets are
        # opt-in via ?status=. Visibility itself is enforced by the view's
        # base queryset, so this can't widen what the caller may see.
        if not self.form.cleaned_data.get("status"):
            queryset = queryset.filter(status_id=Status.PUBLISHED)
        return super().filter_queryset(queryset)

    def filter_q(self, queryset, name, value):
        return search_mapping_sets(queryset, value)

    def filter_creator_id(self, queryset, name, value):
        return queryset.filter(creator_ids__contains=[value])

    def filter_latest(self, queryset, name, value):
        if not value:
            return queryset
        # The highest version is picked among the caller-visible sets with the
        # requested statuses, so other filters (e.g. q) narrow the result
        # rather than surfacing an older version that happens to match.
        statuses = self.form.cleaned_data.get("status") or [Status.PUBLISHED]
        candidates = self.queryset.filter(status_id__in=statuses)
        newest = (
            candidates.filter(series_id=OuterRef("series_id"))
            .order_by(version_order().desc(), "-created_at", "-pk")
            .values("pk")[:1]
        )
        return queryset.filter(pk=Subquery(newest))


def version_order() -> Cast:
    """
    set_version as integers ([1, 2, 0] for 1.2.0, [2026, 11, 4] for
    2026-11-04). Every version of a set_uri is SemVer or every one is an ISO
    date (enforced on import), so this orders a set's versions by release.
    """
    return Cast(
        Func(F("set_version"), Value("[.-]"), function="regexp_split_to_array"),
        ArrayField(IntegerField()),
    )


class MappingFilter(filters.FilterSet):
    q = filters.CharFilter(
        method="filter_q",
        help_text="Fuzzy search over subject/object labels and CURIEs.",
    )
    subject_id = filters.CharFilter(
        field_name="subject__canonical_iri", help_text="Exact subject CURIE."
    )
    object_id = filters.CharFilter(
        field_name="object__canonical_iri", help_text="Exact object CURIE."
    )
    predicate = CharInFilter(field_name="predicate_id")
    predicate_modifier = filters.ChoiceFilter(choices=PredicateModifier.choices)
    justification = CharInFilter(field_name="mapping_justification_id")
    confidence_min = filters.NumberFilter(field_name="confidence", lookup_expr="gte")
    mapping_set = UUIDInFilter(field_name="mapping_set_id")
    object_source = filters.CharFilter(
        field_name="mapping_set__object_source", lookup_expr="iexact"
    )
    term_level = filters.ChoiceFilter(
        field_name="subject__ext_term_level", choices=TermLevel.choices
    )

    class Meta:
        model = Mapping
        fields: list[str] = []

    def filter_q(self, queryset, name, value):
        # Resolve q to terms first (trigram scan on the small Term table, using
        # its GIN indexes), then join mappings on the FK indexes.
        if not value.strip():
            return queryset
        term_ids = search_terms(Term.objects.all(), value).values("pk")
        return queryset.filter(Q(subject_id__in=term_ids) | Q(object_id__in=term_ids))


class TermFilter(filters.FilterSet):
    q = filters.CharFilter(
        method="filter_q", help_text="Fuzzy search over label and CURIE."
    )
    kind = filters.ChoiceFilter(choices=TermKind.choices)
    prefix = filters.CharFilter(field_name="prefix", lookup_expr="iexact")
    term_level = filters.ChoiceFilter(
        field_name="ext_term_level", choices=TermLevel.choices
    )

    class Meta:
        model = Term
        fields: list[str] = []

    def filter_q(self, queryset, name, value):
        return search_terms(queryset, value)


class RelevanceOrderingFilter(OrderingFilter):
    """
    ``OrderingFilter`` that, when a fuzzy ``q`` search was applied and no
    explicit ``?ordering=`` is given, orders by search relevance instead of
    the view's default ordering (which is then used as the tiebreak).
    """

    def filter_queryset(self, request, queryset, view):
        explicit = request.query_params.get(self.ordering_param)
        if not explicit and "match_rank" in queryset.query.annotations:
            return order_by_relevance(
                queryset, *(getattr(view, "ordering", None) or ())
            )
        return super().filter_queryset(request, queryset, view)

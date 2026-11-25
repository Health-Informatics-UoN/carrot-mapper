"""
Visibility rules for registry reads.

Reads are public. What a caller may see depends on the set's status:

- PUBLISHED: everyone, and listed/searched by default.
- WITHDRAWN: everyone, by id or with an explicit ``status`` filter; hidden
  from default listings and from cross-set search.
- DRAFT: only the user who submitted the import, and registry admins.

Cross-set endpoints (``mappings/``, ``terms/``) only ever cover PUBLISHED
sets, so search results never point at withdrawn or draft content.
"""

from django.db.models import Exists, OuterRef, Q, QuerySet

from registry.models import Mapping, MappingSet, MappingSetSeries, Status, Term


def is_registry_admin(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def visible_mapping_sets(user) -> QuerySet[MappingSet]:
    """Every set ``user`` may resolve by id (any status they are allowed)."""
    qs = MappingSet.objects.all()
    if is_registry_admin(user):
        return qs

    visible = Q(status_id__in=[Status.PUBLISHED, Status.WITHDRAWN])
    if user and user.is_authenticated:
        visible |= Q(import_job__submitted_by=user)
    return qs.filter(visible)


def visible_series(user) -> QuerySet[MappingSetSeries]:
    """Every series with at least one version ``user`` may see."""
    return MappingSetSeries.objects.filter(
        Exists(visible_mapping_sets(user).filter(series=OuterRef("pk")))
    )


def published_mappings() -> QuerySet[Mapping]:
    return Mapping.objects.filter(mapping_set__status_id=Status.PUBLISHED)


def published_terms() -> QuerySet[Term]:
    """Terms used by at least one mapping in a PUBLISHED set."""
    published = published_mappings()
    return Term.objects.filter(
        Exists(published.filter(subject=OuterRef("pk")))
        | Exists(published.filter(object=OuterRef("pk")))
    )

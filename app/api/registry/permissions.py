"""
Who may see, and change the status of, registry content.

Reads are public. What a caller may see depends on the set's status:

- PUBLISHED: everyone, and listed/searched by default.
- WITHDRAWN: everyone, by id or with an explicit ``status`` filter; hidden
  from default listings and from cross-set search.
- DRAFT: its publisher (who submitted the import), the owner of its mapping
  set (MappingSetSeries.publisher), and registry admins.

Cross-set endpoints (``mappings/``, ``terms/``) only ever cover PUBLISHED
sets, so search results never point at withdrawn or draft content.

The status of a version (publish, withdraw) can be changed by the same users
who may see its drafts: CanManageMappingSetVersion.
"""

from django.db.models import Exists, OuterRef, Q, QuerySet
from rest_framework.permissions import BasePermission

from registry.models import Mapping, MappingSet, MappingSetSeries, Status, Term


def is_registry_admin(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def can_manage_version(user, mapping_set: MappingSet) -> bool:
    """A registry admin, the version's publisher, or its mapping set's owner."""
    if is_registry_admin(user):
        return True
    if not (user and user.is_authenticated):
        return False
    return user.pk in (mapping_set.publisher_id, mapping_set.series.publisher_id)


class CanManageMappingSetVersion(BasePermission):
    """For a MappingSet (one version): see can_manage_version."""

    def has_object_permission(self, request, view, obj) -> bool:
        return can_manage_version(request.user, obj)


def visible_mapping_sets(user) -> QuerySet[MappingSet]:
    """Every set ``user`` may resolve by id (any status they are allowed)."""
    qs = MappingSet.objects.all()
    if is_registry_admin(user):
        return qs

    visible = Q(status_id__in=[Status.PUBLISHED, Status.WITHDRAWN])
    if user and user.is_authenticated:
        # The publisher is the import's submitter, copied so it outlives the job.
        visible |= (
            Q(import_job__submitted_by=user)
            | Q(publisher=user)
            | Q(series__publisher=user)
        )
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

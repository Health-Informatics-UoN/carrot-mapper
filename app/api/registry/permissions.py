"""
Who may see, and change the status of, registry content.

Reads are public. What a caller may see depends on the set's status:

- PUBLISHED: everyone, and listed/searched by default.
- WITHDRAWN: everyone, by id or with an explicit ``status`` filter; hidden
  from default listings and from cross-set search.
- DRAFT: only its publisher (who submitted the import), and registry admins.

Cross-set endpoints (``mappings/``, ``terms/``) only ever cover PUBLISHED
sets, so search results never point at withdrawn or draft content.

A set's status can be changed by its publisher and by registry admins.
"""

from django.db.models import Exists, OuterRef, Q, QuerySet

from rest_framework.permissions import BasePermission

from registry.models import ImportJob, Mapping, MappingSet, Status, Term


def is_registry_admin(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


class IsPublisherOrRegistryAdmin(BasePermission):
    """For a MappingSet: the user who published it, or a registry admin."""

    def has_object_permission(self, request, view, obj) -> bool:
        return is_registry_admin(request.user) or (
            obj.publisher_id is not None and obj.publisher_id == request.user.pk
        )


def visible_mapping_sets(user) -> QuerySet[MappingSet]:
    """Every set ``user`` may resolve by id (any status they are allowed)."""
    qs = MappingSet.objects.all()
    if is_registry_admin(user):
        return qs

    visible = Q(status_id__in=[Status.PUBLISHED, Status.WITHDRAWN])
    if user and user.is_authenticated:
        visible |= Q(publisher=user)
    return qs.filter(visible)


def visible_import_jobs(user) -> QuerySet[ImportJob]:
    """The import jobs ``user`` may read: their own, or any for registry admins."""
    qs = ImportJob.objects.all()
    if is_registry_admin(user):
        return qs
    if user and user.is_authenticated:
        return qs.filter(submitted_by=user)
    return qs.none()


def published_mappings() -> QuerySet[Mapping]:
    return Mapping.objects.filter(mapping_set__status_id=Status.PUBLISHED)


def published_terms() -> QuerySet[Term]:
    """Terms used by at least one mapping in a PUBLISHED set."""
    published = published_mappings()
    return Term.objects.filter(
        Exists(published.filter(subject=OuterRef("pk")))
        | Exists(published.filter(object=OuterRef("pk")))
    )

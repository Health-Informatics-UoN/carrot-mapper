"""
Carrot Mappings Registry (CMR)

Phase 1 data models:

Mapping sets are stored in SSSOM shape: a MappingSet (set-level metadata)
contains many Mappings, each linking a subject Term to an object Term via
a Predicate, with a MappingJustification.
"""

import uuid

from django.conf import settings
from django.db import models
from mapping.models import ScanReport

# ---------------------------------------------------------------------------
# Reference / controlled vocabulary tables
# ---------------------------------------------------------------------------


class Predicate(models.Model):
    """SSSOM predicate, keyed by CURIE, e.g. ``skos:exactMatch``."""

    predicate_id = models.CharField(max_length=255, primary_key=True)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_recommended = models.BooleanField(default=False)

    def __str__(self):
        return self.predicate_id


class License(models.Model):
    """License under which a mapping set is published."""

    id = models.CharField(max_length=255, primary_key=True)
    license_iri = models.URLField(max_length=500, unique=True)
    spdx_id = models.CharField(max_length=100, blank=True, default="")
    label = models.CharField(max_length=255)
    version = models.CharField(max_length=50, blank=True, default="")
    is_open = models.BooleanField(default=True)

    def __str__(self):
        return self.label


class MappingJustification(models.Model):
    """SEMAPV justification, keyed by CURIE, e.g. ``semapv:ManualMappingCuration``."""

    justification_id = models.CharField(max_length=255, primary_key=True)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    def __str__(self):
        return self.justification_id


class Origin(models.Model):
    """How a mapping set entered the registry (CARROT_DIRECT_PUBLISH | SSSOM_UPLOAD)."""

    CARROT_DIRECT_PUBLISH = "CARROT_DIRECT_PUBLISH"
    SSSOM_UPLOAD = "SSSOM_UPLOAD"

    id = models.CharField(max_length=64, primary_key=True)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    def __str__(self):
        return self.id


class Status(models.Model):
    """Lifecycle status of a mapping set (DRAFT | PUBLISHED | WITHDRAWN)."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    WITHDRAWN = "WITHDRAWN"

    id = models.CharField(max_length=64, primary_key=True)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "statuses"

    def __str__(self):
        return self.id


# ---------------------------------------------------------------------------
# Import tracking
# ---------------------------------------------------------------------------


class ImportJobStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"


class ImportJob(models.Model):
    """Tracks one publish/import attempt into the registry."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="registry_import_jobs",
    )
    status = models.CharField(
        max_length=16,
        choices=ImportJobStatus.choices,
        default=ImportJobStatus.PENDING,
    )
    validation_issues = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["submitted_by", "-created_at"])]

    def __str__(self):
        return f"ImportJob {self.id} ({self.status})"


# ---------------------------------------------------------------------------
# Main entities
# ---------------------------------------------------------------------------


class MappingSet(models.Model):
    """An SSSOM mapping set: one versioned, publishable collection of mappings."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    set_uri = models.CharField(max_length=500)
    set_version = models.CharField(max_length=100)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    license = models.ForeignKey(
        License,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mapping_sets",
    )
    origin = models.ForeignKey(
        Origin, on_delete=models.PROTECT, related_name="mapping_sets"
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        default=Status.DRAFT,
        related_name="mapping_sets",
    )
    import_job = models.ForeignKey(
        ImportJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mapping_sets",
    )
    # Only populated when origin = CARROT_DIRECT_PUBLISH.
    source_scan_report = models.ForeignKey(
        ScanReport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registry_mapping_sets",
    )
    curie_map = models.JSONField(default=dict, blank=True)
    extra_metadata = models.JSONField(default=dict, blank=True)
    # Storage key of the original/generated SSSOM file.
    file_key = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["set_uri", "set_version"],
                name="registry_mappingset_uri_version_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "-published_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.set_version})"


class TermKind(models.TextChoices):
    SUBJECT = "SUBJECT", "Subject"
    OBJECT = "OBJECT", "Object"


class Term(models.Model):
    """A subject or object entity referenced by mappings (e.g. a source value or OMOP concept)."""

    id = models.BigAutoField(primary_key=True)
    canonical_iri = models.CharField(max_length=1000)
    label = models.TextField(blank=True, default="")
    type = models.CharField(max_length=255, blank=True, default="")
    category = models.CharField(max_length=255, blank=True, default="")
    prefix = models.CharField(max_length=255, blank=True, default="")
    kind = models.CharField(max_length=16, choices=TermKind.choices)
    # Only meaningful when kind = OBJECT (e.g. OMOP vocabulary version).
    object_source_version = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["canonical_iri", "kind"],
                name="registry_term_iri_kind_uniq",
            ),
        ]
        indexes = [models.Index(fields=["prefix"])]

    def __str__(self):
        return self.canonical_iri


class Mapping(models.Model):
    """A single SSSOM mapping row: subject --predicate--> object."""

    id = models.BigAutoField(primary_key=True)
    mapping_set = models.ForeignKey(
        MappingSet, on_delete=models.CASCADE, related_name="mappings"
    )
    subject = models.ForeignKey(
        Term, on_delete=models.PROTECT, related_name="subject_mappings"
    )
    predicate = models.ForeignKey(
        Predicate, on_delete=models.PROTECT, related_name="mappings"
    )
    object = models.ForeignKey(
        Term, on_delete=models.PROTECT, related_name="object_mappings"
    )
    mapping_justification = models.ForeignKey(
        MappingJustification, on_delete=models.PROTECT, related_name="mappings"
    )
    ext_source_table = models.CharField(max_length=255, blank=True, default="")
    ext_source_field = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return f"{self.subject_id} {self.predicate_id} {self.object_id}"

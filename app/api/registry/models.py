"""
Carrot Mappings Registry (CMR)

Phase 1 data models:

Mapping sets are stored in SSSOM shape: a MappingSet (set-level metadata)
contains many Mappings, each linking a subject Term to an object Term via
a Predicate, with a MappingJustification.
"""

import uuid
from urllib.parse import quote

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


class TermLevel(models.TextChoices):
    FIELD = "FIELD", "Field"
    VALUE = "VALUE", "Value"


# CURIE prefix for Carrot subject terms. Must be declared in each
# MappingSet.curie_map as {CARROT_TERM_PREFIX: CARROT_TERM_NAMESPACE}.
# The namespace does not need to resolve; it is an identifier only.
CARROT_TERM_PREFIX = "carrot"
CARROT_TERM_NAMESPACE = "https://w3id.org/carrot/term/"


class Term(models.Model):
    """
    A subject or object entity referenced by mappings.

    Subject terms (kind = SUBJECT) come from Carrot source data, at field or
    value level. Their canonical_iri is a dataset-independent CURIE, so the
    same field/value across datasets is one reusable term:

        field level:  carrot:{field}
        value level:  carrot:{field}/{value}

    Each segment is percent-encoded (see build_subject_curie), so ':' or '/'
    inside names cannot break parsing. The structured parts are also stored
    in the ext_* columns (exported as declared SSSOM extension slots), so
    consumers never need to parse the identifier or the label.

    Subjects imported from SSSOM files may be any source term and carry no
    ext_* data; those columns are only set for Carrot-shaped subjects.

    Object terms (kind = OBJECT) are the target OMOP concepts, e.g.
    SNOMED:22298006; the ext_* columns are always blank for them.
    """

    id = models.BigAutoField(primary_key=True)
    canonical_iri = models.CharField(max_length=1000)
    # Human-readable only; never parsed.
    label = models.TextField(blank=True, default="")
    type = models.CharField(max_length=255, blank=True, default="")
    category = models.CharField(max_length=255, blank=True, default="")
    prefix = models.CharField(max_length=255, blank=True, default="")
    kind = models.CharField(max_length=16, choices=TermKind.choices)
    # Only meaningful when kind = OBJECT (e.g. OMOP vocabulary version).
    object_source_version = models.CharField(max_length=255, blank=True, default="")

    # SSSOM extension slots, only for kind = SUBJECT.
    ext_term_level = models.CharField(
        max_length=16, choices=TermLevel.choices, blank=True, default=""
    )
    ext_source_field = models.CharField(max_length=255, blank=True, default="")
    # Blank unless ext_term_level = VALUE.
    ext_source_value = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["canonical_iri", "kind"],
                name="registry_term_iri_kind_uniq",
            ),
            models.CheckConstraint(
                condition=(
                    # No source structure: allowed for any term. Always the
                    # case for objects (OMOP concepts), and for subjects that
                    # come from SSSOM uploads without Carrot ext_* columns.
                    models.Q(
                        ext_term_level="",
                        ext_source_field="",
                        ext_source_value="",
                    )
                    # Field-level subject terms have field, no value.
                    | models.Q(
                        kind=TermKind.SUBJECT,
                        ext_term_level=TermLevel.FIELD,
                        ext_source_value="",
                    )
                    & ~models.Q(ext_source_field="")
                    # Value-level subject terms have field + value.
                    | models.Q(
                        kind=TermKind.SUBJECT,
                        ext_term_level=TermLevel.VALUE,
                    )
                    & ~models.Q(ext_source_field="")
                    & ~models.Q(ext_source_value="")
                ),
                name="registry_term_ext_consistent",
            ),
        ]
        indexes = [models.Index(fields=["prefix"])]

    def __str__(self):
        return self.canonical_iri

    @staticmethod
    def build_subject_curie(field: str, value: str | None = None) -> str:
        """Build the canonical CURIE for a Carrot subject term (percent-encoded segments)."""
        parts = [field] if value is None else [field, value]
        return f"{CARROT_TERM_PREFIX}:" + "/".join(quote(p, safe="") for p in parts)


class MappingCardinality(models.TextChoices):
    ONE_TO_ONE = "1:1", "1:1"
    ONE_TO_MANY = "1:n", "1:n"
    MANY_TO_ONE = "n:1", "n:1"
    MANY_TO_MANY = "n:n", "n:n"


class Mapping(models.Model):
    """
    A single SSSOM mapping row: subject --predicate--> object.

    A subject term with several target concepts appears on several rows
    (one per object), with mapping_cardinality = 1:n.
    """

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
    mapping_cardinality = models.CharField(
        max_length=3, choices=MappingCardinality.choices, blank=True, default=""
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["mapping_set", "subject", "predicate", "object"],
                name="registry_mapping_assertion_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.subject_id} {self.predicate_id} {self.object_id}"

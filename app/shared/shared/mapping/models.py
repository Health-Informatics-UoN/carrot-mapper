from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.constraints import UniqueConstraint
from shared.data.models import Concept

STATUS_LIVE = "LIVE"
STATUS_ARCHIVED = "ARCHIVED"
STATUS_CHOICES = [
    (STATUS_LIVE, "Live"),
    (STATUS_ARCHIVED, "Archived"),
]


class CreationType(models.TextChoices):
    Manual = "M", "Manual"
    Vocab = "V", "Vocab"
    Reuse = "R", "Reuse"


class VisibilityChoices(models.TextChoices):
    PUBLIC = "PUBLIC", "Public"
    RESTRICTED = "RESTRICTED", "Restricted"


class BaseModel(models.Model):
    """
    Abstract base model that provides common fields for all models.

    Attributes:
        created_at (DateTimeField): The timestamp when the object was created.
        updated_at (DateTimeField): The timestamp when the object was last updated.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UploadStatus(models.Model):
    value = models.CharField(max_length=64)
    display_name = models.CharField(max_length=64)


class MappingStatus(models.Model):
    value = models.CharField(max_length=64, db_index=True)
    display_name = models.CharField(max_length=64)


class DataPartner(BaseModel):
    """
    Model for a DataPartner.

    Attributes:
        name (CharField): The name of the data partner, limited to 64 characters.
    """

    name = models.CharField(max_length=64)

    class Meta:
        verbose_name = "Data Partner"
        verbose_name_plural = "Data Partners"
        constraints = [
            UniqueConstraint(fields=["name"], name="datapartner_name_unique")
        ]
        app_label = "mapping"

    def __str__(self):
        return str(self.id)


class OmopTable(BaseModel):
    """
    Model for a OmopTable.

    Attributes:
        table: Name of the linking table.
    """

    table = models.CharField(max_length=64, db_index=True)

    class Meta:
        app_label = "mapping"

    def __str__(self):
        return str(self.id)


class OmopField(BaseModel):
    """
    Model for an OmopField.

    Attributes:
        table: FK to `OmopTable`
        field: name of the linking field.
    """

    table = models.ForeignKey(OmopTable, on_delete=models.CASCADE)
    field = models.CharField(max_length=64)

    class Meta:
        app_label = "mapping"
        indexes = [
            models.Index(fields=["table", "field"], name="idx_omop_table_field"),
        ]

    def __str__(self):
        return str(self.id)


class ScanReportConcept(BaseModel):
    """
    Model for Concepts informed by the user or automatic tools.
    It uses a generic relation to connect it to a ScanReportValue or ScanReportValue
    """

    concept = models.ForeignKey(Concept, on_delete=models.DO_NOTHING)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    confidence = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Confidence score for the mapping rule",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the mapping rule",
    )
    mapping_tool = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        default="carrot-mapper",
        help_text="Name of the tool used to create this mapping",
    )
    mapping_tool_version = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text="Version of the mapping tool used",
    )

    # save how the mapping rule was created
    creation_type = models.CharField(
        max_length=1,
        choices=CreationType.choices,
        default=CreationType.Manual,
        db_index=True,
    )

    class Meta:
        app_label = "mapping"
        indexes = [
            models.Index(
                fields=["object_id", "content_type"],
                name="idx_sr_concept_obj_content",
            ),
            models.Index(
                fields=["object_id", "content_type", "concept"],
                name="idx_src_obj_content_concept",
            ),
            models.Index(
                fields=["creation_type", "content_type"],
                name="idx_src_creation_content",
            ),
        ]

    def __str__(self):
        return str(self.id)


class ScanReport(BaseModel):
    """
    Model for a Scan Report.
    """

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=256)  # TODO: rename to `file_name`
    dataset = models.CharField(max_length=128)  # TODO: rename to `name`
    hidden = models.BooleanField(default=False)
    upload_status = models.ForeignKey(
        "UploadStatus",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
        related_name="upload_status",
    )
    upload_status_details = models.TextField(null=True, blank=True)
    mapping_status = models.ForeignKey(
        "MappingStatus",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
        related_name="mapping_status",
    )
    data_dictionary = models.ForeignKey(
        "DataDictionary",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="data_dictionary",
    )
    # TODO: rename to `dataset`
    parent_dataset = models.ForeignKey(
        "Dataset",
        on_delete=models.CASCADE,
        related_name="scan_reports",
        related_query_name="scan_report",
        null=True,
        blank=True,
    )
    visibility = models.CharField(
        max_length=10,
        choices=VisibilityChoices.choices,
        default=VisibilityChoices.PUBLIC,
    )
    viewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="scanreport_viewings",
        related_query_name="scanreport_viewing",
        blank=True,
    )
    editors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="scanreport_editors",
        related_query_name="scanreport_editor",
        blank=True,
    )

    class Meta:
        app_label = "mapping"
        indexes = [
            models.Index(
                fields=["parent_dataset", "hidden"],
                name="idx_sr_dataset_hidden",
            ),
            models.Index(
                fields=["parent_dataset", "hidden", "mapping_status"],
                name="idx_sr_dataset_status",
            ),
        ]

    def __str__(self):
        return str(self.id)


class ScanReportTable(BaseModel):
    """
    Model for a Scan Report Table
    """

    scan_report = models.ForeignKey(ScanReport, on_delete=models.CASCADE)
    name = models.CharField(max_length=256, db_index=True)

    # Quick notes:
    # - "ScanReportField", instead of ScanReportField,
    #    because ScanReportField has yet been defined, so you get a crash
    #    Using the quotes to look up via the name, works just fine
    # - related_name needed to be set because of
    #   https://stackoverflow.com/questions/41595364/fields-e304-reverse-accessor-clashes-in-django
    person_id = models.ForeignKey(
        "ScanReportField",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="person_id",
    )
    date_event = models.ForeignKey(
        "ScanReportField",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="date_event",
    )
    trigger_reuse = models.BooleanField(default=True)

    class Meta:
        app_label = "mapping"

    def __str__(self):
        return str(self.id)


class ScanReportField(BaseModel):
    """
    Model for a Scan Report Field.
    """

    scan_report_table = models.ForeignKey(ScanReportTable, on_delete=models.CASCADE)
    name = models.CharField(max_length=512, db_index=True)
    description_column = models.CharField(max_length=512)
    type_column = models.CharField(max_length=32)
    ignore_column = models.CharField(max_length=64, blank=True, null=True)
    is_patient_id = models.BooleanField(default=False)
    is_ignore = models.BooleanField(default=False)
    classification_system = models.CharField(max_length=64, blank=True, null=True)
    pass_from_source = models.BooleanField(default=True)
    field_description = models.CharField(max_length=256, blank=True, null=True)
    concepts = GenericRelation(ScanReportConcept)

    class Meta:
        app_label = "mapping"

    def __str__(self):
        return str(self.id)


class MappingRule(BaseModel):
    """
    Model for a Mapping Rule.
    """

    # save the scan_report link to make it easier when performing lookups on scan_report_id
    scan_report = models.ForeignKey(ScanReport, on_delete=models.CASCADE)

    # connect the rule to a destination_field (and therefore destination_table)
    # e.g. condition_concept_id
    omop_field = models.ForeignKey(OmopField, on_delete=models.CASCADE)

    # connect the rule with a source_field (and therefore source_table)
    source_field = models.ForeignKey(
        ScanReportField, on_delete=models.CASCADE, null=True, blank=True
    )
    concept = models.ForeignKey(ScanReportConcept, on_delete=models.CASCADE)
    approved = models.BooleanField(default=False)

    class Meta:
        app_label = "mapping"
        indexes = [
            models.Index(
                fields=["scan_report", "concept"],
                name="idx_mappingrule_sr_concept",
            ),
            models.Index(
                fields=["omop_field", "source_field"],
                name="idx_maprule_omop_scr_fields",
            ),
        ]

    def __str__(self):
        return str(self.id)


class ScanReportValue(BaseModel):
    """
    Model for a Scan Report Value.
    """

    scan_report_field = models.ForeignKey(ScanReportField, on_delete=models.CASCADE)
    value = models.CharField(max_length=128, db_index=True)
    frequency = models.IntegerField()
    conceptID = models.IntegerField(default=-1)  # TODO rename it to concept_id
    concepts = GenericRelation(ScanReportConcept)
    value_description = models.CharField(
        max_length=512, blank=True, null=True, db_index=True
    )

    class Meta:
        app_label = "mapping"
        indexes = [
            models.Index(
                fields=["scan_report_field", "value"],
                name="idx_sr_value_field_value",
            ),
        ]

    def __str__(self):
        return str(self.id)


class DataDictionary(BaseModel):
    """
    Model for a Data Dictionary file.
    """

    name = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        app_label = "mapping"

    def __str__(self):
        return str(self.id)


class Dataset(BaseModel):
    """
    Model for datasets which contain scan reports.
    """

    name = models.CharField(max_length=100, unique=True)
    data_partner = models.ForeignKey(
        DataPartner,
        on_delete=models.CASCADE,
        related_name="datasets",
        related_query_name="dataset",
    )
    visibility = models.CharField(
        max_length=10,
        choices=VisibilityChoices.choices,
        default=VisibilityChoices.PUBLIC,
    )
    viewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="dataset_viewings",
        related_query_name="dataset_viewing",
        blank=True,
    )
    admins = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="dataset_admins",
        related_query_name="dataset_admin",
        blank=True,
    )
    editors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="dataset_editors",
        related_query_name="dataset_editor",
        blank=True,
    )
    hidden = models.BooleanField(default=False, db_index=True)
    # `projects` field added by M2M field in `Project`
    # `scan_reports` field added by FK field in `ScanReport`

    class Meta:
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"
        app_label = "mapping"

    def __str__(self) -> str:
        return str(self.id)


class Project(BaseModel):
    """
    Model for projects which are made up of datasets.
    """

    name = models.CharField(max_length=100, unique=True)
    datasets = models.ManyToManyField(
        Dataset, related_name="projects", related_query_name="project", blank=True
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="projects", related_query_name="project"
    )

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        app_label = "mapping"

    def __str__(self) -> str:
        return str(self.id)

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from registry.models import (
    ImportJob,
    ImportJobStatus,
    License,
    Mapping,
    MappingJustification,
    MappingSet,
    Predicate,
    Status,
    Term,
)


class LicenseSerializer(serializers.ModelSerializer):
    """
    Expose licence metadata used when
    selecting a registry licence.
    """

    class Meta:
        model = License
        fields = ["id", "license_iri", "label", "is_open", "is_deprecated"]


class ScanReportRegistryPublishSerializer(serializers.Serializer):
    """Set-level metadata for publishing a scan report's mappings to the registry."""

    title = serializers.CharField(max_length=500)
    set_version = serializers.CharField(max_length=100)
    license = serializers.PrimaryKeyRelatedField(queryset=License.objects.all())
    description = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=[Status.DRAFT, Status.PUBLISHED],
        default=Status.PUBLISHED,
        help_text="Status of the mapping set once the import succeeds.",
    )
    include_author_orcid_ids = serializers.BooleanField(
        default=False,
        help_text=(
            "Write the ORCID iD of each mapping's author (author_id) in the "
            "published file. The publishing user's ORCID iD (creator_id) is "
            "always included when their profile has one."
        ),
    )


class MappingSetWithdrawSerializer(serializers.Serializer):
    reason = serializers.CharField(
        max_length=2000,
        help_text="Why the set is withdrawn; shown with the set.",
    )


UPLOAD_STATUS_CHOICES = [Status.DRAFT, Status.PUBLISHED]


class RegistryUploadSerializer(serializers.Serializer):
    """
    An SSSOM upload. The file must carry its own metadata: fields here are the
    only request options, and anything else is refused rather than ignored.
    """

    file = serializers.FileField(allow_empty_file=True)
    status = serializers.ChoiceField(
        choices=UPLOAD_STATUS_CHOICES,
        default=Status.PUBLISHED,
        help_text="The set's status once the import succeeds.",
    )

    def validate(self, attrs):
        unsupported = set(self.initial_data) - set(self.fields)
        if unsupported:
            raise serializers.ValidationError(
                {name: "This option is not supported." for name in unsupported}
            )
        return attrs


class ValidationIssueSerializer(serializers.Serializer):
    level = serializers.ChoiceField(choices=["error", "warning"])
    code = serializers.CharField()
    message = serializers.CharField()
    line = serializers.IntegerField(required=False)
    column = serializers.CharField(required=False)


class RegistryUploadValidationSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    issues = ValidationIssueSerializer(many=True)
    set_uri = serializers.CharField()
    set_version = serializers.CharField()
    title = serializers.CharField()
    license = serializers.CharField(allow_null=True)
    rows_checked = serializers.IntegerField()


class RegistryUploadAcceptedSerializer(serializers.Serializer):
    import_job_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=ImportJobStatus.choices)
    issues = ValidationIssueSerializer(many=True)


class RegistryImportAcceptedSerializer(serializers.Serializer):
    import_job_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=ImportJobStatus.choices)


# ---------------------------------------------------------------------------
# Read: vocabularies
# ---------------------------------------------------------------------------


class PredicateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Predicate
        fields = ["predicate_id", "label", "description", "is_recommended"]


class MappingJustificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MappingJustification
        fields = ["justification_id", "label", "description"]


# ---------------------------------------------------------------------------
# Read: terms, mapping sets, mappings
# ---------------------------------------------------------------------------


class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = [
            "id",
            "canonical_iri",
            "label",
            "kind",
            "prefix",
            "type",
            "category",
            "object_source_version",
            "ext_term_level",
            "ext_source_field",
            "ext_source_value",
        ]


class MappingSetBriefSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="status_id")

    class Meta:
        model = MappingSet
        fields = ["id", "set_uri", "set_version", "title", "status"]


class ImportJobSerializer(serializers.ModelSerializer):
    """A registry import's progress, for its submitter to poll."""

    origin = serializers.CharField(source="origin_id")
    mapping_set = serializers.SerializerMethodField()

    class Meta:
        model = ImportJob
        fields = [
            "id",
            "status",
            "origin",
            "validation_issues",
            "error_message",
            "stats",
            "mapping_set",
            "created_at",
            "started_at",
            "finished_at",
        ]

    @extend_schema_field(MappingSetBriefSerializer(allow_null=True))
    def get_mapping_set(self, job):
        # Until the job succeeds, any set it has loaded is not finished.
        if job.status != ImportJobStatus.SUCCEEDED:
            return None
        mapping_sets = job.mapping_sets.all()
        if not mapping_sets:
            return None
        return MappingSetBriefSerializer(mapping_sets[0]).data


class MappingSetListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="status_id")
    origin = serializers.CharField(source="origin_id")
    license = serializers.CharField(source="license_id")
    mapping_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MappingSet
        fields = [
            "id",
            "set_uri",
            "set_version",
            "title",
            "description",
            "status",
            "origin",
            "license",
            "subject_source",
            "subject_source_version",
            "object_source",
            "object_source_version",
            "creator_ids",
            "publication_date",
            "created_at",
            "published_at",
            "mapping_count",
        ]


class ImportProvenanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportJob
        fields = ["id", "status", "origin", "started_at", "finished_at", "stats"]


class MappingSetDetailSerializer(MappingSetListSerializer):
    import_job = ImportProvenanceSerializer(allow_null=True)
    source_scan_report = serializers.PrimaryKeyRelatedField(read_only=True)
    subject_count = serializers.IntegerField(read_only=True)
    object_count = serializers.IntegerField(read_only=True)
    has_file = serializers.SerializerMethodField()

    class Meta(MappingSetListSerializer.Meta):
        fields = MappingSetListSerializer.Meta.fields + [
            "sssom_version",
            "curie_map",
            "extra_metadata",
            "withdrawn_at",
            "withdrawal_reason",
            "import_job",
            "source_scan_report",
            "subject_count",
            "object_count",
            "has_file",
        ]

    def get_has_file(self, obj) -> bool:
        return bool(obj.file_key)


class MappingSerializer(serializers.ModelSerializer):
    subject = TermSerializer()
    predicate = serializers.CharField(source="predicate_id")
    object = TermSerializer()
    mapping_justification = serializers.CharField(source="mapping_justification_id")
    mapping_set = MappingSetBriefSerializer()

    class Meta:
        model = Mapping
        fields = [
            "id",
            "mapping_set",
            "subject",
            "predicate",
            "predicate_modifier",
            "object",
            "mapping_justification",
            "mapping_cardinality",
            "confidence",
            "author_ids",
            "reviewer_ids",
            "mapping_date",
            "comment",
            "extra_metadata",
            "other",
        ]

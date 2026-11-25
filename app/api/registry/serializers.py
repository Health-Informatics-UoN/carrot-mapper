from rest_framework import serializers

from registry.models import (
    ImportJob,
    ImportJobStatus,
    License,
    Mapping,
    MappingJustification,
    MappingSet,
    MappingSetSeries,
    Predicate,
    Status,
    Term,
)
from registry.versions import ReleaseType


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
    release_type = serializers.ChoiceField(
        choices=ReleaseType.choices,
        help_text=(
            "Kind of release; the version is the next SemVer of this kind after "
            "the set's highest version (1.0.0 for the first publish)."
        ),
    )
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


class RegistryImportAcceptedSerializer(serializers.Serializer):
    import_job_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=ImportJobStatus.choices)
    set_version = serializers.CharField()


class NextVersionsSerializer(serializers.Serializer):
    major = serializers.CharField()
    minor = serializers.CharField()
    patch = serializers.CharField()


class RegistryPublishVersionsSerializer(serializers.Serializer):
    """The scan report's highest version and the next one per release type."""

    latest_version = serializers.CharField(allow_null=True)
    next_versions = NextVersionsSerializer()


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
    series = serializers.UUIDField(source="series_id", read_only=True)
    set_uri = serializers.CharField(source="series.set_uri", read_only=True)

    class Meta:
        model = MappingSet
        fields = ["id", "series", "set_uri", "set_version", "title", "status"]


class MappingSetSeriesSerializer(serializers.ModelSerializer):
    """A mapping set and the versions of it the caller may see, newest first."""

    source_scan_report = serializers.PrimaryKeyRelatedField(read_only=True)
    versions = serializers.SerializerMethodField()

    class Meta:
        model = MappingSetSeries
        fields = ["id", "set_uri", "source_scan_report", "created_at", "versions"]

    def get_versions(self, obj) -> list[dict]:
        # Set by the view: only the versions the caller may see.
        return MappingSetBriefSerializer(obj.visible_versions, many=True).data


class MappingSetListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="status_id")
    series = serializers.UUIDField(source="series_id", read_only=True)
    set_uri = serializers.CharField(source="series.set_uri", read_only=True)
    origin = serializers.CharField(source="origin_id")
    license = serializers.CharField(source="license_id")
    mapping_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MappingSet
        fields = [
            "id",
            "series",
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

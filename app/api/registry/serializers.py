from rest_framework import serializers

from registry.models import ImportJobStatus, License, Status


class LicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = License
        fields = ["id", "license_iri", "spdx_id", "label", "is_open", "is_deprecated"]


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
    include_orcid_ids = serializers.BooleanField(required=False)
    include_author_orcid_ids = serializers.BooleanField(required=False)

    def validate(self, attrs):
        legacy_value = attrs.get("include_orcid_ids")
        author_value = attrs.pop("include_author_orcid_ids", None)
        if (
            author_value is not None
            and legacy_value is not None
            and author_value != legacy_value
        ):
            raise serializers.ValidationError(
                {"include_author_orcid_ids": "ORCID flags must have the same value."}
            )
        attrs["include_orcid_ids"] = (
            author_value if author_value is not None else (legacy_value or False)
        )
        return attrs


class RegistryImportAcceptedSerializer(serializers.Serializer):
    import_job_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=ImportJobStatus.choices)

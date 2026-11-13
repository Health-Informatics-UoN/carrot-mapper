from rest_framework import serializers

from registry.models import ImportJobStatus, License, Status


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
    include_orcid_ids = serializers.BooleanField(default=False)


class RegistryImportAcceptedSerializer(serializers.Serializer):
    import_job_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=ImportJobStatus.choices)

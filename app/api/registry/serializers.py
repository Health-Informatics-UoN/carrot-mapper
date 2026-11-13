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
    include_author_orcid_ids = serializers.BooleanField(
        default=False,
        help_text=(
            "Write the ORCID iD of each mapping's author (author_id) in the "
            "published file. The publishing user's ORCID iD (creator_id) is "
            "always included when their profile has one."
        ),
    )


class RegistryImportAcceptedSerializer(serializers.Serializer):
    import_job_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=ImportJobStatus.choices)

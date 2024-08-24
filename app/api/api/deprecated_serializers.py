from drf_dynamic_fields import DynamicFieldsMixin  # type: ignore
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from shared.data.models import Concept
from shared.mapping.models import (
    OmopField,
    OmopTable,
    ScanReport,
    ScanReportField,
    ScanReportTable,
    ScanReportValue,
)
from shared.mapping.permissions import has_editorship, is_admin, is_az_function_user


class ConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Concept
        fields = "__all__"


class ScanReportViewSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    def validate(self, data):
        if request := self.context.get("request"):
            if ds := data.get("parent_dataset"):
                if not (
                    is_az_function_user(request.user)
                    or is_admin(ds, request)
                    or has_editorship(ds, request)
                ):
                    raise PermissionDenied(
                        "You must be an admin of the parent dataset to add a new scan report to it.",
                    )
            else:
                raise NotFound("Could not find parent dataset.")
        else:
            raise serializers.ValidationError(
                "Missing request context. Unable to validate scan report."
            )
        return super().validate(data)

    class Meta:
        model = ScanReport
        fields = "__all__"


class ScanReportTableListSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    def validate(self, data):
        if request := self.context.get("request"):
            if sr := data.get("scan_report"):
                if not (
                    is_az_function_user(request.user)
                    or is_admin(sr, request)
                    or has_editorship(sr, request)
                ):
                    raise PermissionDenied(
                        "You must have editor or admin privileges on the scan report to edit its tables.",
                    )
            else:
                raise NotFound("Could not find the scan report for this table.")
        else:
            raise serializers.ValidationError(
                "Missing request context. Unable to validate scan report table."
            )
        return super().validate(data)

    class Meta:
        model = ScanReportTable
        fields = "__all__"


class ScanReportValueViewSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    value = serializers.CharField(
        max_length=128, allow_blank=True, trim_whitespace=False
    )

    def validate(self, data):
        if request := self.context.get("request"):
            if srf := data.get("scan_report_field"):
                if not (
                    is_az_function_user(request.user)
                    or is_admin(srf, request)
                    or has_editorship(srf, request)
                ):
                    raise PermissionDenied(
                        "You must have editor or admin privileges on the scan report to edit its values.",
                    )
            else:
                raise NotFound("Could not find the scan report field for this value.")
        else:
            raise serializers.ValidationError(
                "Missing request context. Unable to validate scan report value."
            )
        return super().validate(data)

    class Meta:
        model = ScanReportValue
        fields = "__all__"


class ScanReportValueEditSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    value = serializers.CharField(
        max_length=128, allow_blank=True, trim_whitespace=False
    )

    class Meta:
        model = ScanReportValue
        fields = "__all__"


class ScanReportFieldListSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=512, allow_blank=True, trim_whitespace=False
    )
    description_column = serializers.CharField(
        max_length=512, allow_blank=True, trim_whitespace=False
    )

    def validate(self, data):
        if request := self.context.get("request"):
            if srt := data.get("scan_report_table"):
                if not (
                    is_az_function_user(request.user)
                    or is_admin(srt, request)
                    or has_editorship(srt, request)
                ):
                    raise PermissionDenied(
                        "You must have editor or admin privileges on the scan report to edit its fields.",
                    )
            else:
                raise NotFound("Could not find the scan report table for this field.")
        else:
            raise serializers.ValidationError(
                "Missing request context. Unable to validate scan report field."
            )
        return super().validate(data)

    class Meta:
        model = ScanReportField
        fields = "__all__"


class OmopFieldSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = OmopField
        fields = "__all__"


class OmopTableSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = OmopTable
        fields = "__all__"


class ContentTypeSerializer(serializers.Serializer):
    """
    Serializes the content type name.

    Args:
        self: The instance of the class.

    Attributes:
        type_name: The serialized content type name.

    """

    type_name = serializers.CharField(max_length=100)

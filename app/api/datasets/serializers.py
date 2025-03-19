from drf_dynamic_fields import DynamicFieldsMixin  # type: ignore
from rest_framework import serializers
from shared.mapping.models import DataPartner, Dataset
from shared.mapping.permissions import is_admin, is_az_function_user
from projects.serializers import ProjectNameSerializer


class DataPartnerSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = DataPartner
        fields = "__all__"


class DataPartnerNameSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = DataPartner
        fields = ("id", "name")


class DatasetSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = ("id", "name")


class DatasetViewSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = "__all__"


class DatasetAndDataPartnerViewSerializer(
    DynamicFieldsMixin, serializers.ModelSerializer
):
    data_partner = DataPartnerSerializer(read_only=True)

    class Meta:
        model = Dataset
        fields = (
            "id",
            "name",
            "data_partner",
            "admins",
            "visibility",
            "created_at",
            "hidden",
            "projects",
        )


class DatasetViewSerializerV2(DynamicFieldsMixin, serializers.ModelSerializer):
    projects = ProjectNameSerializer(many=True, read_only=True)
    data_partner = DataPartnerNameSerializer(read_only=True)

    class Meta:
        model = Dataset
        fields = (
            "id",
            "name",
            "data_partner",
            "admins",
            "visibility",
            "created_at",
            "hidden",
            "updated_at",
            "projects",
            "viewers",
            "editors",
        )


class DatasetCreateSerializerV2(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = (
            "id",
            "name",
            "data_partner",
            "admins",
            "visibility",
            "created_at",
            "hidden",
            "updated_at",
            "projects",
            "viewers",
            "editors",
        )


class DatasetEditSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    def validate_viewers(self, viewers):
        if request := self.context.get("request"):
            if not (
                is_admin(self.instance, request) or is_az_function_user(request.user)
            ):
                raise serializers.ValidationError(
                    "You must be an admin to change this field."
                )
        return viewers

    def validate_editors(self, editors):
        if request := self.context.get("request"):
            if not (
                is_admin(self.instance, request) or is_az_function_user(request.user)
            ):
                raise serializers.ValidationError(
                    "You must be an admin to change this field."
                )
        return editors

    def validate_admins(self, admins):
        if request := self.context.get("request"):
            if not (
                is_admin(self.instance, request) or is_az_function_user(request.user)
            ):
                raise serializers.ValidationError(
                    "You must be an admin to change this field."
                )
        return admins

    def save(self, **kwargs):
        projects = self.context["projects"]

        if self.instance is not None:
            self.instance = self.update(self.instance, self.validated_data)
            return self.instance
        dataset = Dataset.objects.create(**self.validated_data, projects=projects)
        return dataset

    class Meta:
        model = Dataset
        fields = (
            "id",
            "name",
            "data_partner",
            "admins",
            "visibility",
            "created_at",
            "hidden",
            "updated_at",
            "projects",
            "viewers",
            "editors",
        )

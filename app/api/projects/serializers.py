from drf_dynamic_fields import DynamicFieldsMixin  # type: ignore
from rest_framework import serializers

from mapping.models import Project
from mapping.permissions import is_project_admin
from users.serializers import UserSerializer


class ProjectSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """
    Serialiser for showing all details of a Project. Use in RetrieveViews
    where User is permitted to view a particular Project.
    """

    members = UserSerializer(read_only=True, many=True)
    admins = UserSerializer(read_only=True, many=True)

    class Meta:
        model = Project
        fields = ["id", "name", "members", "admins", "created_at"]


class ProjectNameSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """
    Serialiser for only showing the names of Projects. Use in non-admin ListViews.
    """

    class Meta:
        model = Project
        fields = ["id", "name"]


class ProjectDatasetSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """
    Serialiser for only showing the names of Projects. Use in non-admin ListViews.
    """

    class Meta:
        model = Project
        fields = ["name", "datasets", "members"]


class ProjectCreateSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """
    Serialiser for creating a Project. Any authenticated user may create a
    Project; the creator is automatically added as a member and admin (see
    `ProjectIndex.perform_create`).
    """

    class Meta:
        model = Project
        fields = ["id", "name", "members", "admins", "created_at"]
        extra_kwargs = {
            "members": {"required": False, "allow_empty": True},
            "admins": {"required": False, "allow_empty": True},
        }


class ProjectEditSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """
    Serialiser for editing a Project. Only Project admins may change the
    `members` or `admins` fields.
    """

    def validate_members(self, members):
        if request := self.context.get("request"):
            if not is_project_admin(self.instance, request):
                raise serializers.ValidationError(
                    "You must be an admin to change this field."
                )
        return members

    def validate_admins(self, admins):
        if request := self.context.get("request"):
            if not is_project_admin(self.instance, request):
                raise serializers.ValidationError(
                    "You must be an admin to change this field."
                )
        return admins

    class Meta:
        model = Project
        fields = ["id", "name", "members", "admins", "created_at"]

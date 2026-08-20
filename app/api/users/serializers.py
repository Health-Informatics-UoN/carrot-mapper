from django.contrib.auth.models import User
from mapping.models import DataPartner
from rest_framework import serializers

from .models import Profile


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.

    Serializes the id and username fields.

    Args:
        model (User): The model to be serialized.

        fields (list): The fields to be included in
        the serialized output.
    """

    class Meta:
        model = User
        fields = ("id", "username")


class ProfileDataPartnerSerializer(serializers.ModelSerializer):
    """Serializer for the `DataPartner` nested inside a `Profile`."""

    class Meta:
        model = DataPartner
        fields = ("id", "name")


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for a `Profile`'s Data Partner affiliation and ORCID iD."""

    data_partner = ProfileDataPartnerSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = ("data_partner", "orcid")


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for a user's profile page: their username plus their
    optional Data Partner affiliation and ORCID iD.
    """

    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "profile")


class ProfileEditSerializer(serializers.ModelSerializer):
    """
    Serializer for a user editing their own `Profile`. `data_partner` is
    written by ID (`PrimaryKeyRelatedField`), and read back nested via
    `ProfileSerializer`.
    """

    data_partner = serializers.PrimaryKeyRelatedField(
        queryset=DataPartner.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = Profile
        fields = ("data_partner", "orcid")

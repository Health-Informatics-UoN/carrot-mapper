from django.contrib.auth.models import User
from rest_framework import serializers


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
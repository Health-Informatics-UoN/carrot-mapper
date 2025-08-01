from rest_framework import serializers
from shared.users.serializers import UserSerializer

from .models import FileDownload, FileType


class FileTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileType
        fields = ["value", "display_name"]


class FileDownloadSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    file_type = FileTypeSerializer(read_only=True)

    class Meta:
        model = FileDownload
        fields = [
            "id",
            "scan_report",
            "created_at",
            "name",
            "user",
            "file_type",
            "file_url",
        ]

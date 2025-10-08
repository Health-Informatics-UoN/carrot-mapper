from django.conf import settings
from django.db import models
from mapping.models import ScanReport


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class FileType(models.Model):
    """
    A type of file with a value and display name.

    Args:
        value (str): The internal value representing the file type.
        display_name (str): The name displayed to users for this file type.

    Returns:
        str: The display name of the file type.
    """

    value = models.CharField(max_length=50)
    display_name = models.CharField(max_length=100)

    def __str__(self):
        return str(self.display_name)


class FileDownload(BaseModel):
    """
    A downloadable file linked to a scan report and user.

    Args:
        name (str): The name of the file.
        scan_report (ScanReport): The scan report associated with the file.
        user (User, optional): The user who generated the file. Defaults to None.
        file_type (FileType): The type of the file.
        file_url (str, optional): The URL for downloading the file. Defaults to None.
        deleted_at (datetime, optional): Timestamp when the file was deleted. Defaults to None.

    Returns:
        str: The name of the file.
    """

    name = models.CharField(max_length=255)
    scan_report = models.ForeignKey(ScanReport, on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    file_type = models.ForeignKey(FileType, on_delete=models.CASCADE)
    file_url = models.CharField(max_length=500, null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.name)

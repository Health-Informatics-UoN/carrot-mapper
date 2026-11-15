from rest_framework.exceptions import APIException
from rest_framework import status
from django.utils.text import slugify


class StorageUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = (
        "The mapping set file could not be retrieved, please try again later."
    )
    default_code = "storage_unavailable"


def sssom_download_filename(mapping_set) -> str:
    stem = "-".join(
        part
        for part in (slugify(mapping_set.title), slugify(mapping_set.set_version))
        if part
    )
    return f"{stem or mapping_set.pk}.sssom.tsv"

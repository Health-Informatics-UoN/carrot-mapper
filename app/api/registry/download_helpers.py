from django.utils.text import slugify
from rest_framework import status
from rest_framework.exceptions import APIException


class StorageUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = (
        "The mapping set file could not be retrieved, please try again later."
    )
    default_code = "storage_unavailable"


def sssom_download_filename(mapping_set) -> str:
    # Dots are kept so 1.10.0 and 11.0.0 don't both become "1100".
    version = ".".join(
        slug for slug in map(slugify, mapping_set.set_version.split(".")) if slug
    )
    stem = "-".join(part for part in (slugify(mapping_set.title), version) if part)
    return f"{stem or mapping_set.pk}.sssom.tsv"

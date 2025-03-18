import csv
import os
from io import StringIO
from typing import IO, AnyStr, Iterable, Union

from azure.storage.blob import BlobServiceClient, ContentSettings
from django.http.response import HttpResponse


# def download_data_dictionary_blob(blob_name, container="data-dictionaries"):
#     blob_service_client = BlobServiceClient.from_connection_string(
#         os.environ.get("STORAGE_CONN_STRING")
#     )
#     # Access data as StorageStreamerDownloader class
#     # Decode and split the stream using csv.DictReader()
#     container_client = blob_service_client.get_container_client(container)
#     blob_dict_client = container_client.get_blob_client(blob_name)
#     streamdownloader = blob_dict_client.download_blob()
#     data_dictionary = csv.DictReader(
#         streamdownloader.readall().decode("utf-8").splitlines()
#     )

#     # Set up headers, string buffer and a DictWriter object
#     headers = []
#     buffer = StringIO()

#     headers = ["csv_file_name", "field_name", "code", "value"]
#     writer = csv.DictWriter(
#         buffer,
#         lineterminator="\n",
#         delimiter=",",
#         quoting=csv.QUOTE_NONE,
#         fieldnames=headers,
#     )
#     writer.writeheader()
#     # Remove BOM from start of file if it's supplied.
#     data_dictionary = [
#         {key.replace("\ufeff", ""): value for key, value in d.items()}
#         for d in data_dictionary
#     ]
#     for d in data_dictionary:
#         writer.writerow(d)

#     # Go back to the start of the buffer and return in response
#     buffer.seek(0)

#     response = HttpResponse(buffer, content_type="text/csv")
#     response["Content-Disposition"] = f'attachment; filename="{blob_name}"'

#     return response


def get_blob(blob_name: str, container: str) -> bytes:
    """
    Retrieves a blob from the specified container.

    Args:
        blob_name (str): The name of the blob to retrieve.
        container (str): The name of the container where the blob is stored.

    Returns:
        bytes: The content of the blob.
    """
    blob_service_client = BlobServiceClient.from_connection_string(
        os.environ.get("STORAGE_CONN_STRING")
    )
    container_client = blob_service_client.get_container_client(container)
    blob_client = container_client.get_blob_client(blob_name)

    download_stream = blob_client.download_blob()
    return download_stream.readall()


def delete_blob(blob_name: str, container: str) -> bool:
    """
    Deletes a blob from the specified container.

    Args:
        blob_name (str): The name of the blob to delete.
        container (str): The name of the container where the blob is stored.

    Returns:
        bool: True if the blob was successfully deleted.
    """
    blob_service_client = BlobServiceClient.from_connection_string(
        os.environ.get("STORAGE_CONN_STRING")
    )
    container_client = blob_service_client.get_container_client(container)
    blob_dict_client = container_client.get_blob_client(blob_name)
    # Delete the blob
    blob_dict_client.delete_blob()
    return True


def modify_filename(filename: str, dt: str, rand: str) -> str:
    """
    Modifies a filename by appending a date-time string and a random string to it.

    Args:
        filename (str): The original filename.
        dt (str): The date-time string to append to the filename.
        rand (str): The random string to append to the filename.

    Returns:
        str: The modified filename.
    """
    split_filename = os.path.splitext(str(filename))
    return f"{split_filename[0]}_{dt}_{rand}{split_filename[1]}"


def upload_blob(
    blob_name: str,
    container: str,
    file: Union[bytes, str, Iterable[AnyStr], IO[AnyStr]],
    content_type: str,
):
    """
    This function takes a file and uploads it to a specified container in Azure Blob Storage.
    The file is stored with the provided blob name and content type.

    Args:
        blob_name (str): The name that will be assigned to the uploaded file in Azure Blob Storage.
        container (str): The name of the Azure Blob Storage container where the file will be uploaded.
        file (File): The file to be uploaded.
        content_type (str): The MIME type of the file to be uploaded.

    Returns:
        None
    """
    blob_service_client = BlobServiceClient.from_connection_string(
        os.getenv("STORAGE_CONN_STRING")
    )

    blob_client = blob_service_client.get_blob_client(
        container=container, blob=blob_name
    )
    blob_client.upload_blob(
        file.open(),
        content_settings=ContentSettings(content_type=content_type),
    )


def upload_blob_read(
    blob_name: str,
    container: str,
    file: Union[bytes, str, Iterable[AnyStr], IO[AnyStr]],
    content_type: str,
):
    """
    This function takes a file and uploads it to a specified container in Azure Blob Storage.
    The file is stored with the provided blob name and content type.

    TODO: This should be combined with `upload_blob`, but they work slightly differently.

    Args:
        blob_name (str): The name that will be assigned to the uploaded file in Azure Blob Storage.
        container (str): The name of the Azure Blob Storage container where the file will be uploaded.
        file (File): The file to be uploaded.
        content_type (str): The MIME type of the file to be uploaded.

    Returns:
        None
    """
    blob_service_client = BlobServiceClient.from_connection_string(
        os.getenv("STORAGE_CONN_STRING")
    )

    blob_client = blob_service_client.get_blob_client(
        container=container, blob=blob_name
    )
    blob_client.upload_blob(
        file.read(),
        content_settings=ContentSettings(content_type=content_type),
    )

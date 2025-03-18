import csv
import logging
import os
from io import BytesIO
from typing import IO, Any, AnyStr, Dict, Iterable, Optional, Tuple, Union

import openpyxl  # type: ignore
from azure.storage.blob import BlobServiceClient  # type: ignore
from azure.storage.blob import ContentSettings
from shared_code.utils import (process_four_item_dict, process_three_item_dict,
                               remove_BOM)

logger = logging.getLogger("test_logger")


class StorageService:
    def __init__(self):
        self._client = None
        self._storage_type = os.getenv("STORAGE_TYPE")

    def _get_service_client(self):
        if self._client is None:
            if self._storage_type == "azure":
                try:
                    storage_conn_string = os.getenv("STORAGE_CONN_STRING")
                    if not storage_conn_string:
                        raise ValueError(
                            "STORAGE_CONN_STRING environment variable is not set."
                        )

                    self._client = BlobServiceClient.from_connection_string(
                        storage_conn_string
                    )
                    if self._client is None:
                        raise Exception(
                            "Error connecting to Azure Blob Storage. Azure Blob client is None."
                        )

                    logger.info("Successfully initialized BlobServiceClient.")
                    return self._client

                except Exception as e:
                    logger.error(f"Error connecting to Azure Blob Storage: {e}")
                    raise
            else:
                raise Exception(
                    "Storage type not supported. Only Azure Blob Storage is supported."
                )
        return self._client

    def get_scan_report(self, blob: str) -> openpyxl.Workbook:
        """
        Retrieves a scan report from a blob storage and returns it as a Workbook.

        Args:
            blob (str): The name of the scan report blob.

        Returns:
            Workbook: The scan report as an openpyxl Workbook object.
        """
        try:
            # Set Storage Account connection string
            blob_service_client = self._get_service_client()

            # Grab scan report data from blob
            streamdownloader = (
                blob_service_client.get_container_client("scan-reports")
                .get_blob_client(blob)
                .download_blob()
            )
            scanreport_bytes = BytesIO(streamdownloader.readall())

            return openpyxl.load_workbook(
                scanreport_bytes, data_only=True, keep_links=False, read_only=True
            )

        except Exception as e:
            raise ValueError(f"Error getting the scan report: {e}")

    def get_data_dictionary(
        self,
        blob: str,
    ) -> Tuple[
        Optional[Dict[str, Dict[str, Any]]], Optional[Dict[str, Dict[str, Any]]]
    ]:
        if blob is None or blob == "None":
            return None, None

        try:
            blob_service_client = self._get_service_client()

            # Access data as StorageStreamerDownloader class
            # Decode and split the stream using csv.reader()
            dict_client = blob_service_client.get_container_client("data-dictionaries")
            blob_dict_client = dict_client.get_blob_client(blob)

            # Grab all rows with 4 elements for use as value descriptions
            data_dictionary_intermediate = [
                row
                for row in csv.DictReader(
                    blob_dict_client.download_blob()
                    .readall()
                    .decode("utf-8")
                    .splitlines()
                )
                if row["value"] != ""
            ]
            # Remove BOM from start of file if it's supplied.
            dictionary_data = remove_BOM(data_dictionary_intermediate)

            # Convert to nested dictionaries, with structure
            # {tables: {fields: {values: value description}}}
            data_dictionary = process_four_item_dict(dictionary_data)

            # Grab all rows with 3 elements for use as possible vocabs
            vocab_dictionary_intermediate = [
                row
                for row in csv.DictReader(
                    blob_dict_client.download_blob()
                    .readall()
                    .decode("utf-8")
                    .splitlines()
                )
                if row["value"] == ""
            ]
            vocab_data = remove_BOM(vocab_dictionary_intermediate)

            # Convert to nested dictionaries, with structure
            # {tables: {fields: vocab}}
            vocab_dictionary = process_three_item_dict(vocab_data)
            return data_dictionary, vocab_dictionary

        except Exception as e:
            raise ValueError(f"Error getting the data dictionary : {e}")

    def get_blob(self, blob_name: str, container: str) -> bytes:
        """
        Retrieves a blob from the specified container.

        Args:
            blob_name (str): The name of the blob to retrieve.
            container (str): The name of the container where the blob is stored.

        Returns:
            bytes: The content of the blob.
        """
        try:
            blob_service_client = self._get_service_client()

            container_client = blob_service_client.get_container_client(container)
            blob_client = container_client.get_blob_client(blob_name)

            download_stream = blob_client.download_blob()
            return download_stream.readall()

        except Exception as e:
            raise ValueError(f"Error getting the blob : {e}")

    def delete_blob(self, blob_name: str, container: str) -> bool:
        """
        Deletes a blob from the specified container.

        Args:
            blob_name (str): The name of the blob to delete.
            container (str): The name of the container where the blob is stored.

        Returns:
            bool: True if the blob was successfully deleted.
        """
        try:
            blob_service_client = self._get_service_client()

            container_client = blob_service_client.get_container_client(container)
            blob_dict_client = container_client.get_blob_client(blob_name)
            # Delete the blob
            blob_dict_client.delete_blob()
            return True

        except Exception as e:
            raise ValueError(f"Error deleting the blob : {e}")

    def modify_filename(self, filename: str, dt: str, rand: str) -> str:
        """
        Modifies a filename by appending a date-time string and a random string to it.

        Args:
            filename (str): The original filename.
            dt (str): The date-time string to append to the filename.
            rand (str): The random string to append to the filename.

        Returns:
            str: The modified filename.
        """
        try:
            split_filename = os.path.splitext(str(filename))
            return f"{split_filename[0]}_{dt}_{rand}{split_filename[1]}"
        except Exception as e:
            raise ValueError(f"Error modifying the filename : {e}")

    def upload_blob(
        self,
        blob_name: str,
        container: str,
        file: Union[bytes, str, Iterable[AnyStr], IO[AnyStr]],
        content_type: str,
        use_read_method: bool = False,
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
        try:
            blob_service_client = self._get_service_client()

            blob_client = blob_service_client.get_blob_client(
                container=container, blob=blob_name
            )
            file_content = self._read_file(file, use_read_method)
            blob_client.upload_blob(
                file_content,
                content_settings=ContentSettings(content_type=content_type),
            )
        except Exception as e:
            raise ValueError(f"Error uploading the blob: {e}")

    def _read_file(self, file, use_read_method: bool):
        if use_read_method:
            read_file = file.read()
            return read_file

        else:
            open_file = file.open()
            return open_file

    def upload_form_from_data_dictionary_to_containers(
        self, form_value_1, form_value_2, container_1, container_2, blob_1, blob_2
    ):
        """
        Uploads two files from the form to their respective containers in Azure Blob Storage.

        Args:
            form_value_1: The file object for the first file (e.g., scan report).
            form_value_2: The file object for the second file (e.g., data dictionary).
            container_1 (str): The name of the first container (e.g., "scan-reports").
            container_2 (str): The name of the second container (e.g., "data-dictionaries").
            blob_1 (str): The name of the first blob (e.g., scan_report.name).
            blob_2 (str): The name of the second blob (e.g., data_dictionary.name).

        Returns:
            None
        """
        try:
            # Initialise the connection
            blob_service_client = self._get_service_client()

            # Upload the first file to the first container
            blob_client = blob_service_client.get_blob_client(
                container=container_1, blob=blob_1
            )

            # upload the first form value to the first container
            blob_client.upload_blob(form_value_1)

            # Upload the second file to the second container
            blob_client = blob_service_client.get_blob_client(
                container=container_2, blob=blob_2
            )

            #  upload the second form value to the second container
            blob_client.upload_blob(form_value_2)

        except Exception as e:
            raise ValueError(
                f"Error uploading form from upload_form_from_data_dictionary_to_containers: {e}"
            )

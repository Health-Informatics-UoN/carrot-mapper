import csv
import logging
import os
from io import BytesIO
from typing import IO, Any, AnyStr, Dict, Iterable, Optional, Tuple, Union

import openpyxl  # type: ignore
from azure.storage.blob import BlobServiceClient  # type: ignore
from azure.storage.blob import ContentSettings
from minio import Minio
from shared.services.utils import (
    process_four_item_dict,
    process_three_item_dict,
    remove_BOM,
)

logger = logging.getLogger("test_logger")


class StorageService:
    def __init__(self):
        """
        Service for interacting with cloud storage
        providers (Azure Blob Storage and MinIO).
        """
        self._client = None
        self._storage_type = os.getenv("STORAGE_TYPE")

    def _get_service_client(self) -> Optional[Union[BlobServiceClient, Minio]]:
        """
        Initialize the storage service with
        configuration from environment variables.
        """
        # Lazy initialisation
        if self._client is None:
            # ----- Initialising Azure Blob as a Storage -----
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
                    raise ValueError("Failed to initialize Azure Blob Storage client.")

            # ----- Initialising MinIO as a Storage -----

            elif self._storage_type == "minio":
                try:
                    minio_endpoint = os.getenv("MINIO_ENDPOINT")
                    minio_access_key = os.getenv("MINIO_ACCESS_KEY")
                    minio_secret_key = os.getenv("MINIO_SECRET_KEY")

                    if (
                        not minio_endpoint
                        or not minio_access_key
                        or not minio_secret_key
                    ):
                        raise ValueError(
                            "MINIO_ENDPOINT, MINIO_ACCESS_KEY, or \
                                MINIO_SECRET_KEY environment variables are not set."
                        )

                    logger.info(f"Connecting to MinIO at: {minio_endpoint}")

                    self._client = Minio(
                        endpoint=minio_endpoint,
                        access_key=minio_access_key,
                        secret_key=minio_secret_key,
                        secure=False,
                    )
                    logger.info("Successfully initialized MinIO client.")
                    return self._client

                except Exception as e:
                    logger.error(f"Error connecting to MinIO: {e}")
                    raise ValueError(f"Failed to initialize MinIO client: {e}")

            else:
                raise Exception(
                    "Storage type not supported. Only Azure Blob Storage & MinIO is supported."
                )
        return self._client

    def get_scan_report(self, file_name: str) -> openpyxl.Workbook:
        """
        Retrieves a scan report from the storage (either Azure or MinIO) and
        returns it as a Workbook.

        Args:
            - file_name (str): The name of the scan report file.

        Returns:
            - Workbook: The scan report as an openpyxl Workbook object.
        """

        # Set Storage Account connection string
        client = self._get_service_client()

        if self._storage_type == "azure":
            try:
                # Grab scan report data from Blob Storage
                streamdownloader = (
                    client.get_container_client("scan-reports")
                    .get_blob_client(file_name)
                    .download_blob()
                )
                scanreport_bytes = BytesIO(streamdownloader.readall())
                return openpyxl.load_workbook(
                    scanreport_bytes, data_only=True, keep_links=False, read_only=True
                )
            except Exception as e:
                raise ValueError(f"Error getting the scan report from Azure Blob: {e}")

        elif self._storage_type == "minio":
            try:
                # Grab scan report data from MinIO Storage
                with client.get_object("scan-reports", file_name) as response:
                    scanreport_bytes = BytesIO(response.read())

                # Load the workbook from the BytesIO object using openpyxl
                return openpyxl.load_workbook(
                    scanreport_bytes, data_only=True, keep_links=False, read_only=True
                )
            except Exception as e:
                logger.error(f"Error getting the scan report from MinIO: {e}")
                raise ValueError(f"Error getting the scan report from Minio: {e}")

        else:
            raise Exception(
                "Storage type not supported. Only Azure Blob Storage & MinIO is supported."
            )

    def get_data_dictionary(
        self,
        file: str,
    ) -> Tuple[
        Optional[Dict[str, Dict[str, Any]]], Optional[Dict[str, Dict[str, Any]]]
    ]:
        """
        Retrieves and processes a data dictionary file from storage.

        The file is expected to be a CSV with the following structure:
        - Rows with values represent field value descriptions
        - Rows without values represent field vocabulary definitions

        Args:
            file: Name of the data dictionary file to retrieve

        Returns:
            Tuple containing:
            - Data dictionary (nested dict structure: {tables:
            {fields: {values: description}}})
            - Vocabulary dictionary (nested dict structure: {tables:
            {fields: vocab}})

        Raises:
            ValueError: If there's an error processing the data dictionary
        """
        if file is None or file == "None":
            return None, None

        try:
            # Get the file content in a storage-agnostic way
            content = self._get_dictionary_content(file)

            # Process the content into lines
            lines = content.splitlines()

            # Process data dictionary (rows with values)
            data_dict_reader = csv.DictReader(lines)
            data_dictionary_intermediate = [
                row for row in data_dict_reader if row.get("value", "") != ""
            ]
            dictionary_data = remove_BOM(data_dictionary_intermediate)
            data_dictionary = process_four_item_dict(dictionary_data)

            # Process vocab dictionary (rows without values)
            vocab_dict_reader = csv.DictReader(lines)
            vocab_dictionary_intermediate = [
                row for row in vocab_dict_reader if row.get("value", "") == ""
            ]
            vocab_data = remove_BOM(vocab_dictionary_intermediate)
            vocab_dictionary = process_three_item_dict(vocab_data)

            return data_dictionary, vocab_dictionary

        except Exception as e:
            error_msg = (
                f"Error processing data dictionary from {self._storage_type}: {e}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _get_dictionary_content(self, file: str) -> str:
        """
        Helper method to retrieve data dictionary
        content from storage (Azure Blob Storage and MinIO).

        Args:
            file: Name of the file to retrieve

        Returns:
            str: Decoded content of the file

        Raises:
            ValueError: If storage type is unsupported
            or retrieval fails
        """
        client = self._get_service_client()

        if self._storage_type == "azure":
            dict_client = client.get_container_client("data-dictionaries")
            blob_dict_client = dict_client.get_blob_client(file)
            return blob_dict_client.download_blob().readall().decode("utf-8")

        elif self._storage_type == "minio":
            response = client.get_object("data-dictionaries", file)
            content = response.read().decode("utf-8")
            response.close()
            return content

        else:
            raise ValueError(
                "Storage type not supported. Only Azure Blob Storage & MinIO is supported."
            )

    def get_file(self, file_name: str, container: str) -> bytes:
        """
        Retrieves a blob from the specified container.

        Args:
            - blob_name (str): The name of the blob to retrieve.
            - container (str): The name of the container where
            the blob is stored.

        Returns:
            bytes: The content of the blob.
        """
        client = self._get_service_client()

        if self._storage_type == "azure":
            try:
                container_client = client.get_container_client(container)
                blob_client = container_client.get_blob_client(file_name)

                download_stream = blob_client.download_blob()
                return download_stream.readall()

            except Exception as e:
                raise ValueError(f"Error getting the file from Azure Blob : {e}")

        elif self._storage_type == "minio":
            try:
                response = client.get_object(container, file_name)
                file_content = response.read()
                response.close()
                return file_content

            except Exception as e:
                logger.error(f"Error getting the file from MinIO: {e}")
                raise ValueError(f"Error getting the the file to MinIO: {e}")

        else:
            raise Exception(
                "Storage type not supported. Only Azure Blob Storage & MinIO is supported."
            )

    def delete_file(self, file_name: str, container: str) -> bool:
        """
        Deletes a files from the specified container from
        Azure Blob or MinIO Storage.

        Args:
            file_name (str): The name of the file to delete.
            container (str): The name of the container where
            the blob is stored.

        Returns:
            bool: True if the file was successfully deleted.
        """
        client = self._get_service_client()

        if self._storage_type == "azure":
            try:
                container_client = client.get_container_client(container)
                blob_dict_client = container_client.get_blob_client(file_name)
                blob_dict_client.delete_blob()
                return True

            except Exception as e:
                raise ValueError(
                    f"Error deleting the file from Azure Blob Storage : {e}"
                )

        elif self._storage_type == "minio":
            try:
                client.remove_object(container, file_name)
                return True
            except Exception as e:
                logger.error(f"Error deleting the file from MinIO: {e}")
                raise ValueError(f"Error delete the file to MinIO: {e}")

        else:
            raise Exception(
                "Storage type not supported. Only Azure Blob Storage & MinIO is supported."
            )

    def modify_filename(self, filename: str, dt: str, rand: str) -> str:
        """
        Modifies a filename by appending a date-time string
        and a random string to it.

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

    def upload_file(
        self,
        file_name: str,
        container: str,
        file: Union[bytes, str, Iterable[AnyStr], IO[AnyStr]],
        content_type: str,
        use_read_method: bool = False,
    ):
        """
        This function takes a file and uploads it to a specified
        container in Data Storage.

        The file is stored with the provided blob name and
        content type.

        Args:
            - blob_name (str): The name that will be assigned to the
            uploaded file in Data Storage.
            - container (str): The name of the Data Storage
            container where the file will be uploaded.
            - file (File): The file to be uploaded.
            - content_type (str): The MIME type of the file
            to be uploaded.
            - use_read_method: Whether to call .read() on the file object

        Returns:
            None
        """

        client = self._get_service_client()

        file_content = self._read_file(file, use_read_method)

        try:
            if self._storage_type == "azure":
                try:
                    blob_client = client.get_blob_client(
                        container=container, blob=file_name
                    )
                    blob_client.upload_blob(
                        file_content,
                        content_settings=ContentSettings(content_type=content_type),
                    )
                except Exception as e:
                    raise ValueError(
                        f"Error uploading the file in Azure Blob Storage: {e}"
                    )

            elif self._storage_type == "minio":
                try:
                    client.put_object(
                        container,
                        file_name,
                        data=file_content,
                        length=len(file_content),
                        content_type=content_type,
                    )
                except Exception as e:
                    logger.error(f"Error uploading the file to MinIO: {e}")
                    raise ValueError(f"Error uploading the file to MinIO: {e}")

            else:
                raise ValueError(
                    "Storage type not supported. Only Azure Blob Storage & MinIO is supported."
                )

        except Exception as e:
            logger.error(f"Error uploading the file '{file_name}': {e}")
            raise ValueError(f"Error uploading the file: {e}")

    def _read_file(self, file, use_read_method: bool):
        """
        Helper method to read file content based on input type.

        Args:
            - file: File content in various forms
            - use_read_method: Whether to call .read() on
            the file object.

        Returns:
            bytes: The file content as bytes
        """
        if use_read_method:
            read_file = file.read()
            return read_file

        else:
            open_file = file.open()
            return open_file

    def _upload_minio_to_rules_export(
        self, file_name: str, container: str, file: BytesIO, content_type: str
    ):
        """
        Uploads a file to MinIO storage.

        Args:
            - file_name (str): The name of the file to upload.
            - container (str): The name of the container where
            the file will be stored.
            - file (BytesIO): The file content to upload.
            - content_type (str): The content type of the file.
        """
        client = self._get_service_client()

        if self._storage_type != "minio":
            raise ValueError("This method is only for MinIO storage.")

        try:
            file.seek(0)
            file_size = file.getbuffer().nbytes

            client.put_object(
                container,
                file_name,
                data=file,
                length=file_size,
                content_type=content_type,
            )
        except Exception as e:
            logger.error(f"Error uploading the file to MinIO: {e}")
            raise ValueError(f"Error uploading the file to MinIO: {e}")

    def upload_to_rules_export(self, file_name, file, content_type):
        """
        Uploads a file to the rules-exports container in the
        configured storage.

        Args:
            file_name (str): Name of the file to upload
            file: File content to upload
            content_type (str): MIME type of the file
        """
        container = "rules-exports"

        if self._storage_type == "azure":
            self.upload_file(
                file_name=file_name,
                container=container,
                file=file,
                content_type=content_type,
                use_read_method=True,
            )
        elif self._storage_type == "minio":
            self._upload_minio_to_rules_export(
                file_name=file_name,
                container=container,
                file=file,
                content_type=content_type,
            )
        else:
            raise ValueError(
                f"Unsupported storage type: {self._storage_type}. "
                "Only 'azure' and 'minio' are supported for rules exports."
            )

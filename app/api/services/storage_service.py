import csv
import logging
import os
from enum import StrEnum
from io import BytesIO
from typing import IO, Any, AnyStr, Dict, Iterable, Optional, Tuple, Union
from urllib.parse import urlparse

import boto3
import openpyxl  # type: ignore
from azure.storage.blob import (
    BlobServiceClient,  # type: ignore
    ContentSettings,
)
from botocore.client import BaseClient, Config

from services.utils import (
    process_domain_dict,
    process_four_item_dict,
    process_three_item_dict,
    remove_BOM,
)


class STORAGE_TYPE(StrEnum):
    AZURE = "azure"
    S3 = "s3"


logger = logging.getLogger("test_logger")


def _build_s3_endpoint_url(endpoint: str) -> str:
    """
    Ensures the S3 endpoint URL has the correct scheme (http or https). If the scheme is missing, it defaults to https.

    Args:
        endpoint (str): The S3 endpoint URL.

    Returns:
        str: The S3 endpoint URL with the correct scheme, default https if missing.
    """
    if urlparse(endpoint).scheme in ("http", "https"):
        return endpoint
    return f"https://{endpoint}"


class StorageService:
    def __init__(self):
        """
        Service for interacting with cloud storage
        providers (Azure Blob Storage and S3).
        """
        self._azure_client: Optional[BlobServiceClient] = None
        self._s3_client: Optional[BaseClient] = None  # boto3 S3 client
        self._storage_type = os.getenv("STORAGE_TYPE")
        self._get_service_client()

    def _initialise_azure_client(self):
        """
        Initialises the Azure Blob Storage client.
        """
        try:
            storage_conn_string = os.getenv("STORAGE_CONN_STRING")
            if not storage_conn_string:
                raise ValueError("STORAGE_CONN_STRING environment variable is not set.")
            self._azure_client = BlobServiceClient.from_connection_string(
                storage_conn_string
            )
        except Exception as e:
            logger.error(f"Error connecting to Azure Blob Storage: {e}")
            raise ValueError("Failed to initialise Azure Blob Storage client.")

    def _initialise_s3_client(self):
        """
        Initialises the S3 client (boto3).
        """
        try:
            s3_endpoint = os.getenv("S3_ENDPOINT")
            s3_access_key = os.getenv("S3_ACCESS_KEY")
            s3_secret_key = os.getenv("S3_SECRET_KEY")
            if not s3_endpoint or not s3_access_key or not s3_secret_key:
                raise ValueError(
                    "S3_ENDPOINT, S3_ACCESS_KEY, or S3_SECRET_KEY environment variables are not set."
                )
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=_build_s3_endpoint_url(s3_endpoint),
                aws_access_key_id=s3_access_key,
                aws_secret_access_key=s3_secret_key,
                # Fixed region, as before; S3-compatible servers accept us-east-1
                region_name="us-east-1",
                config=Config(
                    signature_version="s3v4",
                    # RustFS requires path-style addressing
                    s3={"addressing_style": "path"},
                ),
            )
        except Exception as e:
            logger.error(f"Error connecting to S3: {e}")
            raise ValueError(f"Failed to initialise S3 client: {e}")

    def _get_service_client(self):
        """
        Get the service client for the specified storage type.

        Returns:
            Union[BlobServiceClient, BaseClient]: The service client.
        """

        if self._storage_type == STORAGE_TYPE.AZURE:
            if self._azure_client is None:
                self._initialise_azure_client()
            return self._azure_client

        elif self._storage_type == STORAGE_TYPE.S3:
            if self._s3_client is None:
                self._initialise_s3_client()
            return self._s3_client

        else:
            raise ValueError(
                "Storage type not supported. Only Azure Blob Storage & S3 is supported."
            )

    def _s3_read_object(self, bucket: str, key: str) -> bytes:
        """
        Reads an object from S3 and always closes the underlying stream.

        Args:
            bucket (str): The S3 bucket name.
            key (str): The S3 object key.

        Returns:
            bytes: The content of the S3 object.
        """
        body = self._s3_client.get_object(Bucket=bucket, Key=key)["Body"]
        try:
            return body.read()
        finally:
            body.close()

    def get_scan_report(self, file_name: str) -> openpyxl.Workbook:
        """
        Retrieves a scan report from the storage (either Azure or S3) and
        returns it as a Workbook.

        Args:
            - file_name (str): The name of the scan report file.

        Returns:
            - Workbook: The scan report as an openpyxl Workbook object.
        """

        if self._azure_client:
            try:
                # Grab scan report data from Blob Storage
                streamdownloader = (
                    self._azure_client.get_container_client("scan-reports")
                    .get_blob_client(file_name)
                    .download_blob()
                )
                scanreport_bytes = BytesIO(streamdownloader.readall())
                return openpyxl.load_workbook(
                    scanreport_bytes, data_only=True, keep_links=False, read_only=True
                )
            except Exception as e:
                raise ValueError(f"Error getting the scan report from Azure Blob: {e}")

        elif self._s3_client:
            try:
                # Grab scan report data from S3 Storage
                scanreport_bytes = BytesIO(
                    self._s3_read_object("scan-reports", file_name)
                )

                # Load the workbook from the BytesIO object using openpyxl
                return openpyxl.load_workbook(
                    scanreport_bytes, data_only=True, keep_links=False, read_only=True
                )
            except Exception as e:
                logger.error(f"Error getting the scan report from S3: {e}")
                raise ValueError(f"Error getting the scan report from S3: {e}")

        else:
            raise Exception(
                "Storage type not supported. Only Azure Blob Storage & S3 is supported."
            )

    def get_data_dictionary(
        self,
        file: str,
    ) -> Tuple[
        Optional[Dict[str, Dict[str, Any]]],
        Optional[Dict[str, Dict[str, Any]]],
        Optional[Dict[str, Dict[str, Any]]],
    ]:
        """
        Retrieves and processes a data dictionary file from storage.

        The file is expected to be a CSV with the following structure:
        - Rows with values represent field value descriptions
        - Rows without values represent field vocabulary/domain definitions

        Args:
            file: Name of the data dictionary file to retrieve

        Returns:
            Tuple containing:
            - Data dictionary (nested dict structure: {tables:
            {fields: {values: description}}})
            - Vocabulary dictionary (nested dict structure: {tables:
            {fields: vocab}})
            - Domain dictionary (nested dict structure: {tables:
            {fields: domain}}), only populated for fields whose row has a
            non-empty "domain" column

        Raises:
            ValueError: If there's an error processing the data dictionary
        """
        if file is None or file == "None":
            return None, None, None

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

            # Process vocab dictionary (rows without values, with a non-empty code).
            # A domain-only row (empty "code") must NOT end up here with an empty
            # vocabulary_id - that would later blow up the "V-concept" lookup, which
            # requires a real vocabulary_id for every pair it's given.
            vocab_dict_reader = csv.DictReader(lines)
            vocab_dictionary_intermediate = [
                row
                for row in vocab_dict_reader
                if row.get("value", "") == "" and row.get("code", "") != ""
            ]
            vocab_data = remove_BOM(vocab_dictionary_intermediate)
            vocab_dictionary = process_three_item_dict(vocab_data)

            # Process domain dictionary (rows without values, with a non-empty domain)
            domain_dict_reader = csv.DictReader(lines)
            domain_dictionary_intermediate = [
                row
                for row in domain_dict_reader
                if row.get("value", "") == "" and row.get("domain", "") != ""
            ]
            domain_data = remove_BOM(domain_dictionary_intermediate)
            domain_dictionary = process_domain_dict(domain_data)

            return data_dictionary, vocab_dictionary, domain_dictionary

        except Exception as e:
            error_msg = (
                f"Error processing data dictionary from {self._storage_type}: {e}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _get_dictionary_content(self, file: str) -> str:
        """
        Helper method to retrieve data dictionary
        content from storage (Azure Blob Storage and S3).

        Args:
            file: Name of the file to retrieve

        Returns:
            str: Decoded content of the file

        Raises:
            ValueError: If storage type is unsupported
            or retrieval fails
        """

        if self._azure_client:
            dict_client = self._azure_client.get_container_client("data-dictionaries")
            blob_dict_client = dict_client.get_blob_client(file)
            return blob_dict_client.download_blob().readall().decode("utf-8")

        elif self._s3_client:
            return self._s3_read_object("data-dictionaries", file).decode("utf-8")

        else:
            raise ValueError(
                "Storage type not supported. Only Azure Blob Storage & S3 is supported."
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

        if self._azure_client:
            try:
                container_client = self._azure_client.get_container_client(container)
                blob_client = container_client.get_blob_client(file_name)

                download_stream = blob_client.download_blob()
                return download_stream.readall()

            except Exception as e:
                raise ValueError(f"Error getting the file from Azure Blob : {e}")

        elif self._s3_client:
            try:
                return self._s3_read_object(container, file_name)

            except Exception as e:
                logger.error(f"Error getting the file from S3: {e}")
                raise ValueError(f"Error getting the the file to S3: {e}")

        else:
            raise Exception(
                "Storage type not supported. Only Azure Blob Storage & S3 is supported."
            )

    def delete_file(self, file_name: str, container: str) -> bool:
        """
        Deletes a files from the specified container from
        Azure Blob or S3 Storage.

        Args:
            file_name (str): The name of the file to delete.
            container (str): The name of the container where
            the blob is stored.

        Returns:
            bool: True if the file was successfully deleted.
        """

        if self._azure_client:
            try:
                container_client = self._azure_client.get_container_client(container)
                blob_dict_client = container_client.get_blob_client(file_name)
                blob_dict_client.delete_blob()
                return True

            except Exception as e:
                raise ValueError(
                    f"Error deleting the file from Azure Blob Storage : {e}"
                )

        elif self._s3_client:
            try:
                self._s3_client.delete_object(Bucket=container, Key=file_name)
                return True
            except Exception as e:
                logger.error(f"Error deleting the file from S3: {e}")
                raise ValueError(f"Error deleting the file from S3: {e}")

        else:
            raise Exception(
                "Storage type not supported. Only Azure Blob Storage & S3 is supported."
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
        use_s3_bytesio_method: bool = False,
    ):
        """
        This function takes a file and uploads it to a specified
        container in Data Storage.

        The file is stored with the provided blob name and
        content type.

        Uploads a file to storage with special handling for
        S3 rules exports.

        Args:
            - file_name (str): The name that will be assigned to the
            uploaded file in Data Storage.
            - container (str): The name of the Data Storage
            container where the file will be uploaded.
            - file (File): The file to be uploaded.
            - content_type (str): The MIME type of the file
            to be uploaded.
            - use_read_method: Whether to call .read() on the file object
            - use_s3_bytesio_method: Whether to use specific bytesIO upload
            which does not use use_read_method.

        Rules:
            - Azure: Must use `use_read_method=True` (for BytesIO files).

            - Azure: Must use `use_read_method=False` (for other files).

            - S3 Rules Export: Must use `use_s3_bytesio_method=True` for
            direct file handling and for BytesIO files.

            - S3 Rules Export: Must use `use_s3_bytesio_method=False` for
            other file type handling.

        """

        if self._storage_type == STORAGE_TYPE.AZURE and use_s3_bytesio_method:
            raise ValueError("s3_rules_export cannot be used with Azure storage")

        # Handle S3 rules export special case (BytesIO like Files)
        if self._storage_type == STORAGE_TYPE.S3 and use_s3_bytesio_method:
            file.seek(0)
            file_size = file.getbuffer().nbytes
            file_content = file

        else:
            file_content = self._read_file(file, use_read_method)
            file_size = len(file_content)

        if self._s3_client:
            try:
                self._s3_client.put_object(
                    Bucket=container,
                    Key=file_name,
                    Body=file_content,
                    ContentLength=file_size,
                    ContentType=content_type,
                )
                return
            except Exception as e:
                logger.error(f"Error uploading the file to S3: {e}")
                raise ValueError(f"Error uploading the file to S3: {e}")

        elif self._azure_client:
            try:
                blob_client = self._azure_client.get_blob_client(
                    container=container, blob=file_name
                )
                blob_client.upload_blob(
                    file_content,
                    content_settings=ContentSettings(content_type=content_type),
                )
            except Exception as e:
                raise ValueError(f"Error uploading the file in Azure Blob Storage: {e}")

        else:
            raise ValueError(
                "Storage type not supported. Only Azure Blob Storage & S3 is supported."
            )

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

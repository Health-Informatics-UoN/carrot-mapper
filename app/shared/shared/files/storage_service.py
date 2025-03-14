import csv
import logging
import os
from io import BytesIO, StringIO
from typing import IO, Any, AnyStr, Dict, Iterable, Optional, Tuple, Union

import openpyxl  # type: ignore
from azure.storage.blob import (BlobServiceClient,  # type: ignore
                                ContentSettings)
from django.conf import settings  # type: ignore
from django.http.response import HttpResponse  # type: ignore
from shared.files.utils import (process_four_item_dict,
                                process_three_item_dict, remove_BOM)

# Set up logger
logger = logging.getLogger("storage_service_logger")

# ---- Set up the storage service client ----


class StorageService:
    """
    The StorageService class provides methods for uploading,
    downloading, retrieving, file name modification, and deleting
    files from Azure Blob Storage or MinIO.
    """

    def __init__(self):
        """
        Initialises the StorageService class by setting the storage
        type and initialising the storage service client.
        """
        self.storage_type = settings.STORAGE_TYPE
        self._initialise_storage()

    def _initialise_storage(self):
        """
        Initialises the storage service client based on the storage
        type (Azure Blob Storage or MinIO).
        """
        if self.storage_type == "azure":
            self.client = BlobServiceClient.from_connection_string(
                os.getenv("STORAGE_CONN_STRING")
            )
        elif self.storage_type == "minio":
            pass
            # self.client = Minio(
            #     os.getenv("MINIO_ENDPOINT")
            #     .replace("http://", "")
            #     .replace("https://", ""),
            #     access_key=os.getenv("MINIO_ACCESS_KEY"),
            #     secret_key=os.getenv("MINIO_SECRET_KEY"),
            #     secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
            # )

        # ----- Add new storage service clients above this line -----

        else:
            raise ValueError("Invalid storage type. Use only 'azure' or 'minio'.")

    def upload_file(
        self,
        container: str,
        blob_name: str,
        file: Union[bytes, str, Iterable[AnyStr], IO[AnyStr]],
        content_type: str,
        use_read_method=False,
    ):
        """
        Uploads a file to the specified container in the storage
        service (Azure Blob or MinIO).

        Args:
            container (str): The name of the container in which
            to upload the file.

            file (Union[bytes, str, Iterable[AnyStr], IO[AnyStr]]):
            The file to be uploaded.

            blob_name (str): The name of the file in the container.

            content_type (str): The MIME type of the file to be uploaded.

            use_read_method (bool): If True, use `file.read()` instead of
            `file.open()` (for compatibility with `upload_blob_read`).

        Returns:
            None
        """
        if self.storage_type == "azure":
            try:
                blob_client = self.client.get_blob_client(
                    container=container, blob=blob_name
                )

                # Determine the correct method to read the file
                file_content = self._read_file(file, use_read_method)

                blob_client.upload_blob(
                    file_content,
                    content_settings=ContentSettings(content_type=content_type),
                )
            except Exception as e:
                raise ValueError(f"Error uploading file to Azure Blob Storage: {e}")

        elif self.storage_type == "minio":
            try:
                # MinIO: Choose file reading method
                file_content = self._read_file(file, use_read_method)

                # Convert to BytesIO (MinIO requires binary stream)
                if not isinstance(file_content, bytes):
                    file_content = file_content.read()

                file_stream = BytesIO(file_content)
                self.client.upload_fileobj(file_stream, Bucket=container, Key=blob_name)
            except Exception as e:
                raise ValueError(f"Error uploading file to MinIO: {e}")

        # ----- Add new storage service clients logic above this line -----

        else:
            raise ValueError("Invalid storage type. Use only 'azure' or 'minio'.")

    def _read_file(self, file, use_read_method: bool) -> bytes:
        """
        Reads a file based on its type.

        Args:
            file: The file object or file path.
            use_read_method (bool): Whether to use `.read()` or
            `.open()`.

        Returns:
            bytes: The file content as bytes.
        """

        # If file is a string (file path)
        if isinstance(file, str):
            with open(file, "rb") as f:
                return f.read()

        # Use `.read()` method if read is True
        elif use_read_method:
            return file.read()

        # Use `.open()` method if read is False
        else:
            return file.open()

    def delete_file(self, container: str, blob_name: str):
        """
        Deletes a file from the specified container in the storage service.

        Args:
            container (str): The name of the container from which to
            delete the file.

            blob_name (str): The name of the file to delete.

        Returns:
            None
        """
        if self.storage_type == "azure":
            try:
                container_client = self.client.get_container_client(container)
                blob_client = container_client.get_blob_client(blob_name)

                blob_client.delete_blob()
                return True
            except Exception as e:
                raise ValueError(f"Error deleting file from Azure Blob Storage: {e}")

        elif self.storage_type == "minio":
            try:
                self.client.delete_object(Bucket=container, Key=blob_name)
            except Exception as e:
                raise ValueError(f"Error deleting file from Minio: {e}")

        # ----- Add new storage service clients logic above this line -----

        else:
            raise ValueError("Invalid storage type. Use only 'azure' or 'minio'.")

    def get_blob(self, blob_name: str, container: str) -> bytes:
        """
        Retrieves a blob from the specified container.

        Args:
            blob_name (str): The name of the blob to retrieve.

            container (str): The name of the container where the
            blob is stored.

        Returns:
            bytes: The content of the blob.
        """
        if self.storage_type == "azure":
            try:
                container_client = self.client.get_container_client(container)
                blob_client = container_client.get_blob_client(blob_name)

                download_stream = blob_client.download_blob()
                file_content = BytesIO(download_stream.readall())
                return file_content
            except Exception as e:
                raise ValueError(f"Error downloading file from Azure Blob Storage: {e}")

        elif self.storage_type == "minio":
            try:
                file_stream = BytesIO()
                self.client.download_fileobj(
                    Bucket=container, Key=blob_name, Fileobj=file_stream
                )
                file_stream.seek(0)
                return file_stream.read()
            except Exception as e:
                raise ValueError(f"Error downloading file from Minio: {e}")

        # ----- Add new storage service clients logic above this line -----

        else:
            raise ValueError("Invalid storage type. Use only 'azure' or 'minio'.")

    @staticmethod
    def modify_filename(filename: str, dt: str, rand: str) -> str:
        """
        Modifies a filename by appending a date-time string and
        a random string to it.

        Args:
            filename (str): The original filename.

            dt (str): The date-time string to append to the
            filename.

            rand (str): The random string to append to the
            filename.

        Returns:
            str: The modified filename.
        """
        split_filename = os.path.splitext(str(filename))
        return f"{split_filename[0]}_{dt}_{rand}{split_filename[1]}"

    @staticmethod
    def get_scan_report(self, blob_name: str) -> openpyxl.Workbook:
        """
        Retrieves a scan report from a blob storage (Azure or MinIO)
        and returns it as a openpyxl Workbook.

        Args:
            blob_name (str): The name of the scan report blob.

        Returns:
            Workbook: The scan report as an openpyxl Workbook object.
        """
        try:
            if self.storage_type in ["azure", "minio"]:
                scan_report_bytes = self.get_blob(blob_name, "scan-reports")
            else:
                raise ValueError("Invalid storage type. Use only 'azure' or 'minio'.")

            return openpyxl.load_workbook(
                BytesIO(scan_report_bytes),
                data_only=True,
                keep_links=False,
                read_only=True,
            )
        except Exception as e:
            logger.error(f"Error retrieving scan report from {self.storage_type}: {e}")
            raise ValueError(
                f"Error retrieving scan report from {self.storage_type}: {e}"
            )

    @staticmethod
    def get_data_dictionary(
        self, blob_name: str
    ) -> Tuple[
        Optional[Dict[str, Dict[str, Any]]], Optional[Dict[str, Dict[str, Any]]]
    ]:
        """
        Retrieves the data dictionary and vocabulary dictionary
        from a blob storage and MinIO.

        Args:
            blob (str): The name of the blob containing the
            data dictionary.

        Returns:
            Tuple[Optional[Dict[str, Dict[str, Any]]], Optional[Dict[str,
            Dict[str, Any]]]]: A tuple containing the data dictionary
            and vocabulary dictionary.
        """
        if not blob_name or blob_name == "None":
            return None, None

        try:
            # Fetch the file content based on storage type
            if self.storage_type in ["azure", "minio"]:
                content = self.get_blob(blob_name, "data-dictionaries")
            else:
                raise ValueError("Invalid storage type. Use only 'azure' or 'minio'.")

            # Convert bytes content to string
            blob_content_str = content.decode("utf-8")

            # Read CSV data
            csv_reader = csv.DictReader(blob_content_str.splitlines())

            # Separate dictionaries based on whether "value" is empty or not
            data_dictionary_intermediate = []
            vocab_dictionary_intermediate = []

            for row in csv_reader:
                if row.get("value"):
                    data_dictionary_intermediate.append(row)
                else:
                    vocab_dictionary_intermediate.append(row)

            # Remove BOM from the CSV headers
            data_dictionary = remove_BOM(data_dictionary_intermediate)
            vocab_dictionary = remove_BOM(vocab_dictionary_intermediate)

            # Convert processed data into nested dictionaries
            data_dictionary = process_four_item_dict(data_dictionary)
            vocab_dictionary = process_three_item_dict(vocab_dictionary)

            return data_dictionary, vocab_dictionary

        except Exception as e:
            logger.error(f"Error retrieving data dictionary: {e}")
            raise ValueError(
                f"Error retrieving data dictionary from {self.storage_type}: {e}"
            )

    @staticmethod
    def download_data_dictionary(
        self, blob_name: str, container: str = "data-dictionaries"
    ) -> HttpResponse:
        """
        Downloads a data dictionary file from the configured storage
        service (Azure or MinIO) and returns it as an HTTP response.

        Args:
            blob_name (str): The name of the file to be downloaded.

            container (str): The name of the container/bucket.

        Returns:
            HttpResponse: The file contents as a CSV response.
        """
        try:
            if self.storage_type in ["azure", "minio"]:
                file_content = self.get_blob(blob_name, container).decode("utf-8")

            else:
                raise ValueError("Invalid storage type. Use only 'azure' or 'minio'.")

            # Process CSV content
            data_dictionary = csv.DictReader(file_content.splitlines())

            # Set up headers, string buffer, and a DictWriter object
            buffer = StringIO()
            headers = ["csv_file_name", "field_name", "code", "value"]
            writer = csv.DictWriter(
                buffer,
                fieldnames=headers,
                delimiter=",",
                quoting=csv.QUOTE_NONE,
                lineterminator="\n",
            )
            writer.writeheader()

            # Remove BOM from start of file if it's supplied.
            cleaned_data = [
                {key.replace("\ufeff", ""): value for key, value in d.items()}
                for d in data_dictionary
            ]

            for row in cleaned_data:
                writer.writerow(row)

            # Return as an HTTP Response
            buffer.seek(0)
            response = HttpResponse(buffer, content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{blob_name}"'

            return response

        except Exception as e:
            logger.error(f"Error downloading data dictionary: {e}")
            raise ValueError(
                f"Error downloading data dictionary from {self.storage_type}: {e}"
            )

    # ----- Add new methods for the StorageService class above this line -----

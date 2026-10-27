import os
from urllib.parse import urlparse

import boto3
from azure.storage.blob import BlobServiceClient
from botocore.client import BaseClient, Config
from botocore.exceptions import ClientError
from django.core.management.base import BaseCommand


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


class Command(BaseCommand):
    help = "Create required Azure Queues and Blob Containers in Azurite emulator."

    # Get the type of storage to use from the env
    STORAGE_TYPE = os.getenv("STORAGE_TYPE")

    # Get the Azure Connection String from the env
    AZURE_CONN_STRING = os.getenv("STORAGE_CONN_STRING")

    # Get the S3 Storage Connection String from the env
    S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")

    # Define the required queues and blob containers or buckets
    QUEUES = [
        os.getenv("RULES_QUEUE_NAME"),
        os.getenv("WORKERS_RULES_EXPORT_NAME"),
        os.getenv("WORKERS_UPLOAD_NAME"),
    ]

    CONTAINERS = ["scan-reports", "data-dictionaries", "rules-exports", "airflow-logs"]

    def _create_blob_containers(self, blob_service: BlobServiceClient):
        """
        Creates the required Azure Blob Containers.

        Args:
            blob_service: BlobServiceClient instance.

        Returns:
            - Creates blob container if it doesn't exist
            - If the blob container exists, it will skip
            and return a message.
        """
        try:
            for container_name in self.CONTAINERS:
                blob_client = blob_service.get_container_client(container_name)
                if blob_client.exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"Blob container '{container_name}' already exists. Skipping creation."
                        )
                    )
                else:
                    blob_client.create_container()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Blob container '{container_name}' created successfully."
                        )
                    )

        except Exception as e:
            raise ValueError(f"Error when creating Azure Blob Container: {e}")

    @staticmethod
    def _bucket_exists(s3_client: BaseClient, bucket_name: str) -> bool:
        """
        Check if an S3 bucket exists.

        Args:
            s3_client: boto3 S3 client instance.
            bucket_name: Name of the S3 bucket to check.

        Returns:
            bool: True if the bucket exists, False otherwise.

        Raises:
            ClientError: If there is an error checking the bucket existence.
        """
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchBucket"):
                return False
            raise

    def _create_s3_buckets(self, s3_client: BaseClient):
        """
        Creates the required S3 Buckets.

        Args:
            s3_client: boto3 S3 client instance.

        Returns:
            - Creates bucket if it doesn't exist
            - If the bucket exists, it will skip and return a message.
        """
        try:
            for bucket_name in self.CONTAINERS:
                if self._bucket_exists(s3_client, bucket_name):
                    self.stdout.write(
                        self.style.WARNING(
                            f"Bucket '{bucket_name}' already exists. Skipping creation."
                        )
                    )
                else:
                    s3_client.create_bucket(Bucket=bucket_name)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Bucket '{bucket_name}' created successfully."
                        )
                    )
        except ClientError as e:
            raise ValueError(f"Error when creating S3 Bucket: {e}")

    def _create_azure_resources(self):
        """
        Creates the required Azure Queues and Blob Containers to
        run Carrot-Mapper.

        Uses Azure Blob as a storage.

        Args:
            None

        Returns:
            - Creates queues and blob containers if they don't exist
            - If the queues and blob containers exist, it will skip
            and return a message.
        """
        if not self.AZURE_CONN_STRING:
            self.stdout.write(self.style.ERROR("AZURE_CONN_STRING is not set."))
            return

        try:
            blob_service = BlobServiceClient.from_connection_string(
                self.AZURE_CONN_STRING
            )

            # Create Blob Containers
            self._create_blob_containers(blob_service)

            self.stdout.write(self.style.SUCCESS("Azurite Storage setup complete."))

        except Exception as e:
            raise ResourceCreationError(
                f"Error when creating Queue and Container Automatically for Azure: {e}"
            )

    def _create_s3_resources(self):
        """
        Creates the required S3 resources such as S3
        Buckets to run Carrot-Mapper.

        Uses S3 as a storage.

        Args:
            None

        Returns:
            - Creates bucket if it doesn't exist
            - If the bucket exists, it will skip and return a message.
        """
        if not all(
            [
                self.S3_ENDPOINT,
                self.S3_ACCESS_KEY,
                self.S3_SECRET_KEY,
            ]
        ):
            self.stdout.write(
                self.style.ERROR("Required connections for S3 is not set.")
            )
            return

        try:
            # Creates S3 Connection
            s3_client = boto3.client(
                "s3",
                endpoint_url=_build_s3_endpoint_url(self.S3_ENDPOINT),
                aws_access_key_id=self.S3_ACCESS_KEY,
                aws_secret_access_key=self.S3_SECRET_KEY,
                # Fixed region, as before; S3-compatible servers accept us-east-1
                region_name="us-east-1",
                config=Config(
                    signature_version="s3v4",
                    # RustFS requires path-style addressing
                    s3={"addressing_style": "path"},
                ),
            )

            # Create S3 Buckets
            self._create_s3_buckets(s3_client)

            self.stdout.write(self.style.SUCCESS("S3 Storage setup complete."))
        except Exception as e:
            raise ResourceCreationError(
                f"Error when creating Bucket Automatically for S3: {e}"
            )

    def handle(self, *args, **kwargs):
        """
        Handles the creation of resources such as containers and queues
        based on the storage type provided.
        Args:
            None
        Returns:
            - Calls the appropriate method based on the storage type.
            - Creates the required resources.
        """
        if not self.STORAGE_TYPE:
            self.stdout.write(
                self.style.ERROR("STORAGE_TYPE environment variable is not set.")
            )
            return

        # Check the type of storage to use and create the resources

        if self.STORAGE_TYPE.lower() == "azure":
            self._create_azure_resources()
        elif self.STORAGE_TYPE.lower() == "s3":
            self._create_s3_resources()
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"Unsupported STORAGE_TYPE: {self.STORAGE_TYPE}. Use 'azure' or 's3'."
                )
            )


# Custom Error Handling for Configurations


class ResourceCreationError(Exception):
    """Exception raised for errors in creating resources."""

    pass

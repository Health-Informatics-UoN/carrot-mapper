import os

from azure.storage.blob import BlobServiceClient  # type: ignore
from azure.storage.queue import QueueServiceClient  # type: ignore
from django.core.management.base import BaseCommand  # type: ignore
from minio import Minio  # type: ignore


class Command(BaseCommand):
    help = "Create required Azure Queues and Blob Containers in Azurite emulator."

    # Get the type of storage to use from the env
    STORAGE_TYPE = os.getenv("STORAGE_TYPE")

    # Get the Azure Connection String from the env
    AZURE_CONN_STRING = os.getenv("STORAGE_CONN_STRING")

    # Get the MinIO Storage Connection String from the env
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")

    # Define the required queues and blob containers or buckets
    QUEUES = [
        os.getenv("RULES_QUEUE_NAME"),
        os.getenv("WORKERS_RULES_EXPORT_NAME"),
        os.getenv("WORKERS_UPLOAD_NAME"),
    ]

    CONTAINERS = ["scan-reports", "data-dictionaries", "rules-exports", "airflow-logs"]

    def _create_azure_queues(self, queue_service: str):
        """
        Creates the required Azure Queues.

        Args:
            queue_service: QueueServiceClient instance.

        Returns:
            - Creates queue if it doesn't exist
            - If the queue exists, it will skip and
            returns a message.
        """
        try:
            for queue_name in self.QUEUES:
                queue_client = queue_service.get_queue_client(queue_name)
                try:
                    # Check if the queue exists
                    queue_client.get_queue_properties()
                    self.stdout.write(
                        self.style.WARNING(
                            f"Queue '{queue_name}' already exists. Skipping creation."
                        )
                    )
                # If the queue does not exist, create it
                except Exception:
                    queue_client.create_queue()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Queue '{queue_name}' created successfully."
                        )
                    )

        except Exception as e:
            raise ValueError(f"Error when creating Azure Queue: {e}")

    def _create_blob_containers(self, blob_service: str):
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

    def _create_minio_buckets(self, minio_client: str):
        """
        Creates the required MinIO Buckets.

        Args:
            minio_client: MinIO Client instance.

        Returns:
            - Creates bucket if it doesn't exist
            - If the bucket exists, it will skip and return a message.
        """
        try:
            for bucket_name in self.CONTAINERS:
                if minio_client.bucket_exists(bucket_name):
                    self.stdout.write(
                        self.style.WARNING(
                            f"Bucket '{bucket_name}' already exists. Skipping creation."
                        )
                    )
                else:
                    minio_client.make_bucket(bucket_name)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Bucket '{bucket_name}' created successfully."
                        )
                    )
        except ResourceCreationError as e:
            raise ValueError(f"Error when creating MinIO Bucket: {e}")

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
            queue_service = QueueServiceClient.from_connection_string(
                self.AZURE_CONN_STRING
            )
            blob_service = BlobServiceClient.from_connection_string(
                self.AZURE_CONN_STRING
            )

            # Create Queues and Blob Containers
            self._create_azure_queues(queue_service)
            self._create_blob_containers(blob_service)

            self.stdout.write(self.style.SUCCESS("Azurite Storage setup complete."))

        except Exception as e:
            raise ResourceCreationError(
                f"Error when creating Queue and Container Automatically for Azure: {e}"
            )

    def _create_minio_resources(self):
        """
        Creates the required MinIO resources such as MinIO
        Buckets to run Carrot-Mapper.

        Uses MinIO as a storage.

        Args:
            None

        Returns:
            - Creates bucket if it doesn't exist
            - If the bucket exists, it will skip and return a message.
        """
        if not all(
            [
                self.MINIO_ENDPOINT,
                self.MINIO_ACCESS_KEY,
                self.MINIO_SECRET_KEY,
            ]
        ):
            self.stdout.write(
                self.style.ERROR("Required connections for MINIO is not set.")
            )
            return

        try:
            # Creates MinIO Connection
            minio_client = Minio(
                self.MINIO_ENDPOINT,
                access_key=self.MINIO_ACCESS_KEY,
                secret_key=self.MINIO_SECRET_KEY,
                secure=False,
            )

            # Create MinIO Buckets
            self._create_minio_buckets(minio_client)

            self.stdout.write(self.style.SUCCESS("MinIO Storage setup complete."))
        except Exception as e:
            raise ResourceCreationError(
                f"Error when creating Bucket Automatically for MinIO: {e}"
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
        elif self.STORAGE_TYPE.lower() == "minio":
            self._create_minio_resources()
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"Unsupported STORAGE_TYPE: {self.STORAGE_TYPE}. Use 'azure' or 'minio'."
                )
            )


# Custom Error Handling for Configurations


class ResourceCreationError(Exception):
    """Exception raised for errors in creating resources."""

    pass

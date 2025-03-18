import os
from django.core.management.base import BaseCommand  # type: ignore
from azure.storage.queue import QueueServiceClient  # type: ignore
from azure.storage.blob import BlobServiceClient  # type: ignore
from azure.core.exceptions import ResourceExistsError  # type: ignore


class Command(BaseCommand):
    help = "Create required Azure Queues and Blob Containers in Azurite emulator."

    # Get the Storage Connection String from the env
    STORAGE_CONN_STRING = os.getenv("STORAGE_CONN_STRING")

    # Define the required queues and blob containers
    QUEUES = ["rules-local", "rules-exports-local", "uploadreports-local"]
    BLOB_CONTAINERS = ["scan-reports", "data-dictionaries", "rules-exports"]

    def create_queues(self, queue_service: str):
        """
        Creates the required Azure Queues.

        Args:
            queue_service: QueueServiceClient instance

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

    def create_blob_containers(self, blob_service: str):
        """
        Creates the required Azure Blob Containers.

        Args:
            blob_service: BlobServiceClient instance

        Returns:
            - Creates blob container if it doesn't exist
            - If the blob container exists, it will skip and return a message.
        """
        try:
            for container_name in self.BLOB_CONTAINERS:
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

    def handle(self, *args, **kwargs):
        """
        Handles the creation of Azure Queues and Blob Containers.
        """

        storage_conn_string = os.getenv("STORAGE_CONN_STRING")

        if not storage_conn_string:
            self.stdout.write(self.style.ERROR("STORAGE_CONN_STRING is not set."))
            return

        try:
            queue_service = QueueServiceClient.from_connection_string(
                storage_conn_string
            )
            blob_service = BlobServiceClient.from_connection_string(storage_conn_string)

            # Create Queues and Blob Containers
            self.create_queues(queue_service)
            self.create_blob_containers(blob_service)

            self.stdout.write(self.style.SUCCESS("Azurite Storage setup complete."))

        except Exception as e:
            raise ResourceExistsError(
                f"Error when creating Queue and Container Automatically: {e}"
            )

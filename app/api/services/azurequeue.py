import base64
import json
import os
from typing import Any, Dict, Optional

from azure.storage.queue import QueueClient


def add_message(
    queue_name: str,
    message: Dict[str, Any],
    conn_str: Optional[str] = None,
    queue_client: Optional[QueueClient] = None,
) -> None:
    """
    Add a message to the specified Azure Storage Queue.

    Args:
        - queue_name (str): The name of the Azure Storage Queue.
        - message (Dict[str, Any]): The message to be added to the queue.
        - conn_str (str, optional): The connection string for Azure Storage. If not provided, it will be retrieved from environment variables.
        - queue_client (QueueClient, optional): The QueueClient instance. If not provided, it will be created internally.

    Returns:
        - None

    Raises:
        - ValueError: If no connection string can be found.
    """
    # Encode the message
    queue_message = json.dumps(message)
    message_bytes = queue_message.encode("utf-8")
    base64_message = base64.b64encode(message_bytes).decode("utf-8")

    # Get the connection string
    if conn_str is None:
        conn_str = os.environ.get("STORAGE_CONN_STRING")
    if not conn_str:
        raise ValueError("Storage connection string is not provided.")

    if queue_client is None:
        queue_client = QueueClient.from_connection_string(
            conn_str=conn_str, queue_name=queue_name
        )

    queue_client.send_message(base64_message)

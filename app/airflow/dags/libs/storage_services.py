import logging
from pathlib import Path
from typing import Any

from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.microsoft.azure.hooks.wasb import WasbHook
from azure.storage.blob import ContentSettings

from libs.enums import StorageType
from libs.settings import storage_type


def get_storage_hook():
    """
    Returns a storage hook based on the storage type.
    """
    if storage_type == StorageType.AZURE:
        return WasbHook(wasb_conn_id="wasb_conn")
    elif storage_type == StorageType.MINIO:
        return S3Hook(aws_conn_id="minio_conn")
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


def download_blob_to_tmp(container_name: str, blob_name: str) -> Path:
    """
    Downloads a blob from storage to a temporary local file.

    Args:
        container_name (str): The name of the storage container/bucket.
        blob_name (str): The name of the blob/file to download.

    Returns:
        Path: The local path to the downloaded file.
    """
    # TODO: double check temp file can be accessed by other tasks, using KubernetesExecutor
    # https://stackoverflow.com/questions/69294934/where-is-tmp-folder-located-in-airflow
    local_path = Path(f"/tmp/{blob_name}")
    # Storage hook
    storage_hook = get_storage_hook()
    try:
        logging.info(f"Downloading file from {container_name}/{blob_name}")
        if storage_type == StorageType.AZURE:
            storage_hook.get_file(
                file_path=local_path,
                container_name=container_name,
                blob_name=blob_name,
            )
        elif storage_type == StorageType.MINIO:
            s3_object = storage_hook.get_key(key=blob_name, bucket_name=container_name)
            with open(local_path, "wb") as f:
                s3_object.download_fileobj(f)
        return local_path
    except Exception as e:
        logging.error(f"Error downloading {blob_name} from {container_name}: {str(e)}")
        raise


def upload_blob_to_storage(
    container_name: str, blob_name: str, data: Any, content_type: str
) -> None:
    """
    Uploads a blob to storage from a temporary local file.

    Args:
        container_name (str): The name of the storage container/bucket.
        blob_name (str): The name of the blob/file to upload.
        data (Any): The data to upload to the blob.

    Returns:
        None
    """

    # Storage hook
    storage_hook = get_storage_hook()
    try:
        logging.info(
            f"Uploading file to {container_name}/{blob_name}, using {storage_type} storage"
        )
        if storage_type == StorageType.AZURE:
            storage_hook.upload(
                data=data,
                container_name=container_name,
                blob_name=blob_name,
                content_settings=ContentSettings(content_type=content_type),
            )
        elif storage_type == StorageType.MINIO:
            storage_hook.load_file_obj(
                file_obj=data,
                key=blob_name,
                bucket_name=container_name,
                replace=True,
            )
    except Exception as e:
        logging.error(f"Error uploading {blob_name} to {container_name}: {str(e)}")
        raise

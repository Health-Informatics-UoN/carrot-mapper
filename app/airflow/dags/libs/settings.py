import os
from libs.enums import StorageType

storage_type = os.getenv("STORAGE_TYPE", StorageType.MINIO)
AIRFLOW_VAR_WASB_CONNECTION_STRING = os.getenv("AIRFLOW_VAR_WASB_CONNECTION_STRING", "")
AIRFLOW_VAR_MINIO_ENDPOINT = os.getenv("AIRFLOW_VAR_MINIO_ENDPOINT", "")
AIRFLOW_VAR_MINIO_ACCESS_KEY = os.getenv("AIRFLOW_VAR_MINIO_ACCESS_KEY", "")
AIRFLOW_VAR_MINIO_SECRET_KEY = os.getenv("AIRFLOW_VAR_MINIO_SECRET_KEY", "")

# DEBUG MODE: True or False
AIRFLOW_DEBUG_MODE = os.getenv("AIRFLOW_DEBUG_MODE", "false").lower()

# SEARCH ENABLED: Controls whether search recommendations DAG is enabled
SEARCH_ENABLED = os.getenv("SEARCH_ENABLED", "false").lower()

# Timedelta for dagrun_timeout in minutes
AIRFLOW_DAGRUN_TIMEOUT = os.getenv("AIRFLOW_DAGRUN_TIMEOUT", 60)

AIRFLOW_VAR_JSON_VERSION = os.getenv("AIRFLOW_VAR_JSON_VERSION", "v1")

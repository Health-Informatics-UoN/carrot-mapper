import os

from libs.enums import StorageType

storage_type = os.getenv("STORAGE_TYPE", StorageType.MINIO)

# DEBUG MODE: True or False
AIRFLOW_DEBUG_MODE = os.getenv("AIRFLOW_DEBUG_MODE", "false").lower()

# SEARCH ENABLED: Controls whether search recommendations DAG is enabled
SEARCH_ENABLED = os.getenv("SEARCH_ENABLED", "false").lower()

# Timedelta for dagrun_timeout in minutes
AIRFLOW_DAGRUN_TIMEOUT = os.getenv("AIRFLOW_DAGRUN_TIMEOUT", 60)

# In failure callback, temp table cleanup is performed twice.
# This delay (seconds) gives the timed-out task time to finish creating tables.
TEMP_TABLE_CLEANUP_DELAY = int(os.getenv("TEMP_TABLE_CLEANUP_DELAY", "60"))

# Page size for bulk database inserts (execute_values)
EXECUTE_VALUES_PAGE_SIZE = int(os.getenv("EXECUTE_VALUES_PAGE_SIZE", 1000000))

AIRFLOW_VAR_JSON_VERSION = os.getenv("AIRFLOW_VAR_JSON_VERSION", "v1")

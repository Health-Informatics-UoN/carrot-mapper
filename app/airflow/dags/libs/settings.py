import os

from libs.enums import StorageType

storage_type = os.getenv("STORAGE_TYPE", StorageType.S3)

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

# Source of the Mappings Registry license table (license_sync DAG)
SPDX_LICENSE_LIST_URL = os.getenv(
    "SPDX_LICENSE_LIST_URL", "https://spdx.org/licenses/licenses.json"
)

# Carrot Mappings Registry (registry_import DAG)
# Storage container/bucket holding every registry SSSOM file (ImportJob.file_key
# and MappingSet.file_key are blob names inside it).
REGISTRY_SSSOM_CONTAINER = os.getenv("REGISTRY_SSSOM_CONTAINER", "registry-sssom")
# How many imports may run at once. Each holds one DB transaction for its load.
REGISTRY_IMPORT_MAX_ACTIVE_RUNS = int(os.getenv("REGISTRY_IMPORT_MAX_ACTIVE_RUNS", 2))
# Most validation issues stored in ImportJob.validation_issues. A bad file can
# have an issue on every row (a wrong prefix in a 500,000-row file is 500,000
# issues), which would make that JSON column, and the API response that returns
# it, huge. The rest are still counted: an "issues_truncated" entry gives the
# totals. 1000 is plenty to see what's wrong with a file and fix it.
REGISTRY_IMPORT_MAX_ISSUES = int(os.getenv("REGISTRY_IMPORT_MAX_ISSUES", 1000))

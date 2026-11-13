from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import chain
from libs.registry_import.finalize import finalize
from libs.registry_import.full_validate import full_validate
from libs.registry_import.load import load
from libs.registry_import.on_failure import update_import_job_on_failure
from libs.registry_import.prepare_source import prepare_source
from libs.registry_import.validate_params import validate_params_registry_import
from libs.settings import (
    AIRFLOW_DAGRUN_TIMEOUT,
    AIRFLOW_DEBUG_MODE,
    REGISTRY_IMPORT_MAX_ACTIVE_RUNS,
)
from libs.utils import connect_to_storage, create_task

"""
This DAG imports an SSSOM file into the Carrot Mappings Registry. Every publish
path ends as an SSSOM file in storage plus an ImportJob, so this one DAG parses,
validates and loads them all.

Workflow steps:
1. Validate the parameters and mark the ImportJob RUNNING
2. Connect to storage
3. Prepare the source: an upload is already stored; a Mapper direct publish is
   built from the scan report's mappings with the rules SSSOM exporter
4. Fully validate the file (every row), storing the issues on the ImportJob
5. Load it into the registry tables in one transaction (idempotent on retry)
6. Finalize: publish the set (unless a DRAFT was asked for), job SUCCEEDED

On failure the ImportJob is marked FAILED with the reason.
"""

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2026, 11, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    # Problems retrying can't fix raise AirflowFailException and skip retries.
    "retries": 0 if AIRFLOW_DEBUG_MODE == "true" else 3,
    "retry_delay": timedelta(minutes=1),
    "on_failure_callback": update_import_job_on_failure,
}

dag = DAG(
    "registry_import",
    default_args=default_args,
    description="""
    This DAG validates an SSSOM file and imports it into the Carrot Mappings
    Registry as a mapping set.
    """,
    tags=["registry"],
    catchup=False,
    is_paused_upon_creation=False,
    max_active_runs=REGISTRY_IMPORT_MAX_ACTIVE_RUNS,
    dagrun_timeout=timedelta(minutes=float(AIRFLOW_DAGRUN_TIMEOUT)),
    on_failure_callback=update_import_job_on_failure,
)

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

tasks = [
    create_task(
        "validate_params_registry_import", validate_params_registry_import, dag
    ),
    create_task("connect_to_storage", connect_to_storage, dag),
    create_task("prepare_source", prepare_source, dag),
    create_task("full_validate", full_validate, dag),
    create_task("load", load, dag),
    create_task("finalize", finalize, dag),
]

# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

# Execute the tasks in order
chain(start, *tasks, end)

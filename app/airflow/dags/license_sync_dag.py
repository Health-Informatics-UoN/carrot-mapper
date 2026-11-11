from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from libs.license_sync.core import sync_spdx_licenses
from libs.utils import create_task

"""
This DAG keeps the Mappings Registry license table in sync with the SPDX
License List, so licenses never have to be maintained by hand.

Workflow steps:
1. Fetch the SPDX License List and upsert every license into registry_license
"""

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2026, 11, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=10),
}

dag = DAG(
    "license_sync",
    default_args=default_args,
    description="Sync the Mappings Registry license table from the SPDX License List.",
    tags=["registry"],
    schedule="@monthly",
    catchup=False,
    is_paused_upon_creation=False,
    dagrun_timeout=timedelta(minutes=30),
)

start = EmptyOperator(task_id="start", dag=dag)
sync = create_task("sync_spdx_licenses", sync_spdx_licenses, dag)
end = EmptyOperator(task_id="end", dag=dag)

start >> sync >> end

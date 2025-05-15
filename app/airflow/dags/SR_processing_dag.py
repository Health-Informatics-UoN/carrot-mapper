from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from libs.utils import create_task, validate_params_SR_processing
from libs.SR_processing.core import (
    get_scan_report,
    get_data_dictionary,
    create_scan_report_tables,
    create_fields,
)
from libs.SR_processing.utils import connect_to_storage

"""
This DAG automates the process of ...

Workflow steps:

"""

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 3, 25),
    "email_on_failure": False,
    "email_on_retry": False,
    # TODO: modify these settings about retries
    "retries": 0,
}

dag = DAG(
    "scan_report_processing",
    default_args=default_args,
    description=""" ....""",
    tags=["SR_processing"],
    schedule_interval=None,
    catchup=False,
)

# TODO: clean up

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

tasks = [
    create_task("validate_params_SR_processing", validate_params_SR_processing, dag),
    create_task("connect_to_storage", connect_to_storage, dag),
    create_task("get_scan_report", get_scan_report, dag),
    create_task("get_data_dictionary", get_data_dictionary, dag),
    create_task("create_scan_report_tables", create_scan_report_tables, dag),
    create_task("create_fields", create_fields, dag),
]


# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

# Execute the tasks
curr = start
for task in tasks:
    curr >> task
    curr = task
curr >> end

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from libs.utils import create_task, validate_params_SR_processing
from libs.SR_processing.core import (
    process_data_dictionary,
    process_and_create_scan_report_entries,
)
from libs.utils import connect_to_storage

"""
This DAG automates the process of creating scan report tables, fields and values 
from a uploaded scan report and data dictionary.

Workflow steps:
1. Validate the parameters
2. Connect to storage
3. Process the data dictionary
4. Process and create scan report entries (tables, fields and values)
5. Clean up
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
    description="""
    This DAG automates the process of creating scan report tables, fields and values 
    from a uploaded scan report and data dictionary.
    """,
    tags=["SR_processing"],
    schedule_interval=None,
    catchup=False,
    is_paused_upon_creation=False,
)

# TODO: add validate for DD file size: DATA_UPLOAD_MAX_MEMORY_SIZE :(
# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

tasks = [
    create_task("validate_params_SR_processing", validate_params_SR_processing, dag),
    create_task("connect_to_storage", connect_to_storage, dag),
    create_task("process_data_dictionary", process_data_dictionary, dag),
    create_task(
        "process_and_create_scan_report_entries",
        process_and_create_scan_report_entries,
        dag,
    ),
]


# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

# Execute the tasks
curr = start
for task in tasks:
    curr >> task
    curr = task
curr >> end

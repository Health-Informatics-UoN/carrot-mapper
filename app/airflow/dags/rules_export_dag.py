from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from libs.utils import create_task, validate_params_rules_export
from libs.rules_export.core import pre_process_rules, build_and_upload_rules_file
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
    # TODO: add email on failure and retry
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=1),
}

dag = DAG(
    "rules_export",
    default_args=default_args,
    description="""
    This DAG automates the process of retrieving the mapping rules from the database, 
    processing them and then exporting them to a file for downloading.
    """,
    tags=["rules_export"],
    schedule_interval=None,
    catchup=False,
    is_paused_upon_creation=False,
)

# TODO: add validate for DD file size: DATA_UPLOAD_MAX_MEMORY_SIZE :(
# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

tasks = [
    create_task("validate_params_rules_export", validate_params_rules_export, dag),
    create_task("connect_to_storage", connect_to_storage, dag),
    create_task("pre_process_rules", pre_process_rules, dag),
    create_task("build_and_upload_rules_file", build_and_upload_rules_file, dag),
]


# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

# Execute the tasks
curr = start
for task in tasks:
    curr >> task
    curr = task
curr >> end

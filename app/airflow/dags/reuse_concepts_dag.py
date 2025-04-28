from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from libs.core_reuse_concepts import (
    create_temp_reusing_concepts_table,
    find_matching_value,
)
from libs.utils import create_task, validate_params_R_concepts

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
    "reuse_concepts",
    default_args=default_args,
    description="""Find eligible objects for reuse concepts.
    After that, find the dest. table and OMOP field ids for each concept. 
    Eventually, create mapping rules for each reusing concept.""",
    tags=["R-concepts", "mapping_rules_creation"],
    schedule_interval=None,
    catchup=False,
)

# TODO: clean up

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

tasks = [
    create_task("validate_params_R_concepts", validate_params_R_concepts, dag),
    create_task(
        "create_temp_reusing_concepts_table", create_temp_reusing_concepts_table, dag
    ),
    create_task("find_matching_value", find_matching_value, dag),
]


# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

# Execute the tasks
curr = start
for task in tasks:
    curr >> task
    curr = task
curr >> end

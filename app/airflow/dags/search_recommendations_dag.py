from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from libs.utils import create_task
from libs.search_recommendations.core import (
    validate_params_search_recommendations,
    process_search_recommendations,
)
from libs.settings import AIRFLOW_DEBUG_MODE, SEARCH_ENABLED

"""
This DAG generates mapping recommendations using basic string search against the OMOP concept table.

Workflow steps:
1. Validate the parameters
2. Process search recommendations (retrieve values, search concepts, insert recommendations)

The DAG execution is conditional based on the SEARCH_ENABLED environment variable.
"""

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 3, 25),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0 if AIRFLOW_DEBUG_MODE == "true" else 3,
    "retry_delay": timedelta(minutes=1),
}

dag = DAG(
    "search_recommendations",
    default_args=default_args,
    description="""
    This DAG generates mapping recommendations using basic string search against the OMOP concept table.
    It retrieves scan report value strings, searches the OMOP concept table using ILIKE queries,
    and inserts the top 3 matches as MappingRecommendations into the database.
    """,
    tags=["search_recommendations", "mapping"],
    schedule_interval=None,
    catchup=False,
    is_paused_upon_creation=False,
)

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

# Main workflow tasks
tasks = [
    create_task(
        "validate_params_search_recommendations",
        validate_params_search_recommendations,
        dag,
    ),
]

# Conditionally add search task based on environment variable
if SEARCH_ENABLED == "true":
    tasks.append(
        create_task(
            "process_search_recommendations", process_search_recommendations, dag
        )
    )

# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

# Execute the tasks
curr = start
for task in tasks:
    curr >> task
    curr = task
curr >> end

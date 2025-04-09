from datetime import datetime
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from libs.core import find_and_create_standard_concepts

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
    "create_concepts_from_vocab_dict",
    default_args=default_args,
    description="Create standard concepts using vocabulary id from data dictionary for each scan report field",
    tags=["V-concepts"],
    schedule_interval=None,
    catchup=False,
)


# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)


core_task = PythonOperator(
    task_id="find_and_create_standard_concepts",
    python_callable=find_and_create_standard_concepts,
    provide_context=True,
    dag=dag,
)
# TODO: add tasks to do error handling and update status
# TODO: create workflow - deploy MVP - testing

# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

(start >> core_task >> end)

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from libs.core_rules_creation import create_person_rules, create_dates_rules

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
    "create_mapping_rules",
    default_args=default_args,
    description="Create mapping rules for each scan report table based on the available concepts.",
    tags=["mapping_rules_creation"],
    schedule_interval=None,
    catchup=False,
)


# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)


create_person_rules_task = PythonOperator(
    task_id="create_person_rules",
    python_callable=create_person_rules,
    provide_context=True,
    dag=dag,
)

create_dates_rules_task = PythonOperator(
    task_id="create_dates_rules",
    python_callable=create_dates_rules,
    provide_context=True,
    dag=dag,
)


# TODO: add tasks to do error handling and update status


# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

(start >> create_person_rules_task >> create_dates_rules_task >> end)

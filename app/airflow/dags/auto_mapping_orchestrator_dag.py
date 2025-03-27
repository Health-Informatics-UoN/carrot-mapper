from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.empty import EmptyOperator

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 3, 25),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

dag = DAG(
    "auto_mapping_orchestrator",
    default_args=default_args,
    description="Orchestrates the automatic Mapping rules generation workflow",
    schedule_interval=None,
    catchup=False,
    tags=["orchestrator"],
    # Add these settings:
    concurrency=20,  # Allow more concurrent tasks in this DAG
    max_active_runs=5,  # Allow multiple concurrent DAG runs
    dagrun_timeout=timedelta(minutes=60),  # Set a timeout for runs
)

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

# Trigger concept mapping
trigger_create_concepts_vocabs = TriggerDagRunOperator(
    task_id="trigger_create_concepts_from_vocab_dict",
    trigger_dag_id="create_concepts_from_vocab_dict",
    conf={
        "table_id": "{{ dag_run.conf['table_id'] }}",
        "field_vocab_pairs": "{{ dag_run.conf['field_vocab_pairs'] }}",
    },
    wait_for_completion=True,
    dag=dag,
)


# TODO: add this task in the end of Everything
# cleanup_tables = SQLExecuteQueryOperator(
#     task_id="cleanup_tables",
#     sql="""
#     DROP TABLE IF EXISTS temp_sr_values;
#     DROP TABLE IF EXISTS temp_nonstandard_concepts;
#     DROP TABLE IF EXISTS temp_standard_concepts;
#     """,
#     conn_id="1-conn-db",
#     dag=dag,
# )


# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

# Define task dependencies
start >> trigger_create_concepts_vocabs >> end

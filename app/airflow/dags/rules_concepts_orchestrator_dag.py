from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.python import PythonOperator
from airflow.models import Variable, DagRun
from airflow.operators.empty import EmptyOperator

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rules_concepts_orchestrator",
    default_args=default_args,
    description="Orchestrates the RulesConcepts workflow",
    schedule_interval=None,
    catchup=False,
)

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

# Trigger vocabulary processing
trigger_vocab_processing = TriggerDagRunOperator(
    task_id="trigger_vocab_processing",
    trigger_dag_id="vocabulary_processing",
    conf={"concept_id": "{{ dag_run.conf['concept_id'] }}"},
    wait_for_completion=True,
    dag=dag,
)

# # Trigger concept transformation
# trigger_concept_transformation = TriggerDagRunOperator(
#     task_id="trigger_concept_transformation",
#     trigger_dag_id="concept_transformation",
#     conf={"table_id": "{{ dag_run.conf['table_id'] }}"},
#     wait_for_completion=True,
#     dag=dag,
# )

# # Trigger concept creation
# trigger_concept_creation = TriggerDagRunOperator(
#     task_id="trigger_concept_creation",
#     trigger_dag_id="concept_creation",
#     conf={"table_id": "{{ dag_run.conf['table_id'] }}"},
#     wait_for_completion=True,
#     dag=dag,
# )

# # Trigger concept reuse
# trigger_concept_reuse = TriggerDagRunOperator(
#     task_id="trigger_concept_reuse",
#     trigger_dag_id="concept_reuse",
#     conf={"table_id": "{{ dag_run.conf['table_id'] }}"},
#     wait_for_completion=True,
#     dag=dag,
# )

# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

(start >> trigger_vocab_processing >> end)
# (
#     start
#     >> trigger_vocab_processing
#     >> trigger_concept_transformation
#     >> trigger_concept_creation
#     >> trigger_concept_reuse
#     >> end
# )

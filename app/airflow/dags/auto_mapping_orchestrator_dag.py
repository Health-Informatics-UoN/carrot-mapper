from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.empty import EmptyOperator


"""
This DAG orchestrates the automatic mapping rules generation workflow.

Workflow steps:
1. Trigger the concepts_from_vocab_dag to create standard concepts and mapping rules from vocabulary dictionaries
2. Trigger the reuse_concepts_dag to reuse concepts from other scan reports (coming soon)
NOTE: The reuse_concepts_dag will be triggered conditionally based on users's choice.

Requires:
- table_id (int): The ID of the scan report table to process
- person_id_field (int): The ID of the person ID field
- date_event_field (int): The ID of the date event field
- scan_report_id (int): The ID of the scan report to process
- field_vocab_pairs (list): A list of dictionaries containing field-vocab pairs
    For example: 
    "field_vocab_pairs": [
        {
            "sr_field_id": "437",
            "field_data_type": "VARCHAR",
            "vocabulary_id": "ICD10"
        },
        {
            "sr_field_id": "438",
            "field_data_type": "VARCHAR",
            "vocabulary_id": "Gender"
        }
        ]
- parent_dataset_id (int): The ID of the parent dataset where the scan report belongs to (for reuse_concepts_dag (coming soon))

"""


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
    dagrun_timeout=timedelta(minutes=15),  # Set a timeout for runs
)

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

# Trigger concept mapping
trigger_create_concepts_vocabs = TriggerDagRunOperator(
    task_id="trigger_create_concepts_from_vocab_dict",
    trigger_dag_id="create_concepts_from_vocab_dict",
    conf={
        "table_id": "{{ dag_run.conf['table_id'] }}",
        "person_id_field": "{{ dag_run.conf['person_id_field'] }}",
        "date_event_field": "{{ dag_run.conf['date_event_field'] }}",
        "scan_report_id": "{{ dag_run.conf['scan_report_id'] }}",
        "field_vocab_pairs": "{{ dag_run.conf['field_vocab_pairs'] }}",
    },
    wait_for_completion=True,
    dag=dag,
)

#  TODO: add trigger for Reuse concepts here


# TODO: add this task in the end of Everything
# cleanup_temp_table_task = SQLExecuteQueryOperator(
#     task_id="cleanup_temp_table",
#     sql="""
#     DROP TABLE IF EXISTS temp_standard_concepts;
#     """,
#     conn_id="postgres_db_conn",
#     dag=dag,
# )


# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

# Define task dependencies
start >> trigger_create_concepts_vocabs >> end

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.python import PythonOperator
from libs.core import test_add_scan_report_values

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
    "vocabulary_processing",
    default_args=default_args,
    description="Process vocabularies from data dictionary",
    schedule_interval=None,
    catchup=False,
)

# Task to retrieve vocabulary mappings from data dictionary
get_vocab_dictionary = PythonOperator(
    task_id="test_add_scan_report_values",
    python_callable=test_add_scan_report_values,
    op_kwargs={"concept_id": "{{ dag_run.conf['concept_id'] }}"},
    provide_context=True,
    retries=0,
    dag=dag,
)

# # Task to add vocabulary IDs to scan report values
# add_vocabulary_ids = SQLExecuteQueryOperator(
#     task_id="add_vocabulary_ids",
#     sql="""
#     UPDATE scan_report_values srv
#     SET vocabulary_id = dd.code
#     FROM data_dictionary dd
#     JOIN scan_report_fields srf ON srv.scan_report_field_id = srf.id
#     JOIN scan_report_tables srt ON srf.scan_report_table_id = srt.id
#     WHERE srt.id = {{ dag_run.conf["table_id"] }}
#       AND srt.name = dd.csv_file_name
#       AND srf.name = dd.field_name
#     """,
#     conn_id="postgres_default",
#     dag=dag,
# )

# # Task to update job status
# update_job_status = SQLExecuteQueryOperator(
#     task_id="update_job_status",
#     sql="""
#     INSERT INTO job_statuses (table_id, stage, status, details, created_at)
#     VALUES (
#         {{ dag_run.conf["table_id"] }},
#         'BUILD_CONCEPTS_FROM_DICT',
#         'IN_PROGRESS',
#         'Processing vocabulary mappings',
#         NOW()
#     )
#     """,
#     conn_id="postgres_default",
#     dag=dag,
# )

get_vocab_dictionary
# get_vocab_dictionary >> update_job_status >> add_vocabulary_ids

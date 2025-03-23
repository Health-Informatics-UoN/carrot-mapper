from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.sensors.external_task import ExternalTaskSensor

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
    "concept_creation",
    default_args=default_args,
    description="Create scan report concepts",
    schedule_interval=None,
    catchup=False,
)

# Wait for concept transformation to complete
wait_for_transformation = ExternalTaskSensor(
    task_id="wait_for_transformation",
    external_dag_id="concept_transformation",
    external_task_id="process_nonstandard_concepts",
    timeout=600,
    mode="reschedule",
    dag=dag,
)

# Create scan report concepts
create_concepts = SQLExecuteQueryOperator(
    task_id="create_concepts",
    sql="""
    INSERT INTO scan_report_concepts (concept_id, content_type, object_id, source_type)
    SELECT
        srv.concept_id,
        'VALUE',
        srv.id,
        'D'
    FROM scan_report_values srv
    WHERE srv.concept_id != -1
      AND srv.scan_report_field_id IN (
        SELECT id FROM scan_report_fields
        WHERE scan_report_table_id = {{ dag_run.conf["table_id"] }}
      )
    """,
    conn_id="postgres_default",
    dag=dag,
)

# Update job status
update_final_status = SQLExecuteQueryOperator(
    task_id="update_final_status",
    sql="""
    WITH created_concepts AS (
        SELECT COUNT(*) as concept_count
        FROM scan_report_concepts src
        JOIN scan_report_values srv ON src.object_id = srv.id
        WHERE srv.scan_report_field_id IN (
            SELECT id FROM scan_report_fields
            WHERE scan_report_table_id = {{ dag_run.conf["table_id"] }}
        )
        AND src.content_type = 'VALUE'
        AND src.source_type = 'D'
    )
    INSERT INTO job_statuses (table_id, stage, status, details, created_at)
    SELECT
        {{ dag_run.conf["table_id"] }},
        'BUILD_CONCEPTS_FROM_DICT',
        'COMPLETE',
        CASE
            WHEN cc.concept_count = 0 THEN 'Finished'
            ELSE 'Created ' || cc.concept_count || ' concepts based on provided data dictionary.'
        END,
        NOW()
    FROM created_concepts cc
    """,
    conn_id="postgres_default",
    dag=dag,
)

wait_for_transformation >> create_concepts >> update_final_status

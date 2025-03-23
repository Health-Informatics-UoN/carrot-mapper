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
    "concept_reuse",
    default_args=default_args,
    description="Reuse existing concepts",
    schedule_interval=None,
    catchup=False,
)

# Wait for concept creation to complete
wait_for_creation = ExternalTaskSensor(
    task_id="wait_for_creation",
    external_dag_id="concept_creation",
    external_task_id="update_final_status",
    timeout=600,
    mode="reschedule",
    dag=dag,
)

# Start concept reuse
start_reuse = SQLExecuteQueryOperator(
    task_id="start_reuse",
    sql="""
    INSERT INTO job_statuses (table_id, stage, status, details, created_at)
    VALUES (
        {{ dag_run.conf["table_id"] }},
        'REUSE_CONCEPTS',
        'IN_PROGRESS',
        'Starting concept reuse',
        NOW()
    )
    """,
    conn_id="postgres_default",
    dag=dag,
)

# Reuse field concepts
reuse_field_concepts = SQLExecuteQueryOperator(
    task_id="reuse_field_concepts",
    sql="""
    WITH active_concepts AS (
        SELECT src.object_id, src.concept_id
        FROM scan_report_concepts src
        JOIN scan_report_tables srt ON src.scan_report_table_id = srt.id
        WHERE srt.status = 'ACTIVE'
        AND src.content_type = 'FIELD'
    ),
    existing_fields AS (
        SELECT srf.id, srf.name
        FROM scan_report_fields srf
        JOIN active_concepts ac ON srf.id = ac.object_id
    ),
    new_fields AS (
        SELECT srf.id, srf.name
        FROM scan_report_fields srf
        WHERE srf.scan_report_table_id = {{ dag_run.conf["table_id"] }}
    ),
    matched_fields AS (
        SELECT nf.id as new_field_id, ac.concept_id
        FROM new_fields nf
        JOIN existing_fields ef ON nf.name = ef.name
        JOIN active_concepts ac ON ef.id = ac.object_id
    )
    INSERT INTO scan_report_concepts (concept_id, content_type, object_id, source_type)
    SELECT
        mf.concept_id,
        'FIELD',
        mf.new_field_id,
        'R'
    FROM matched_fields mf
    """,
    conn_id="postgres_default",
    dag=dag,
)

# Update job status for field reuse
update_field_reuse_status = SQLExecuteQueryOperator(
    task_id="update_field_reuse_status",
    sql="""
    INSERT INTO job_statuses (table_id, stage, status, details, created_at)
    VALUES (
        {{ dag_run.conf["table_id"] }},
        'REUSE_CONCEPTS',
        'IN_PROGRESS',
        'Finished at field level. Continuing at value level...',
        NOW()
    )
    """,
    conn_id="postgres_default",
    dag=dag,
)

# Reuse value concepts
reuse_value_concepts = SQLExecuteQueryOperator(
    task_id="reuse_value_concepts",
    sql="""
    WITH active_concepts AS (
        SELECT src.object_id, src.concept_id
        FROM scan_report_concepts src
        JOIN scan_report_tables srt ON src.scan_report_table_id = srt.id
        WHERE srt.status = 'ACTIVE'
        AND src.content_type = 'VALUE'
    ),
    existing_values AS (
        SELECT
            srv.id,
            srv.value,
            srv.value_description,
            srf.name as field_name
        FROM scan_report_values srv
        JOIN scan_report_fields srf ON srv.scan_report_field_id = srf.id
        JOIN active_concepts ac ON srv.id = ac.object_id
    ),
    new_values AS (
        SELECT
            srv.id,
            srv.value,
            srv.value_description,
            srf.name as field_name
        FROM scan_report_values srv
        JOIN scan_report_fields srf ON srv.scan_report_field_id = srf.id
        WHERE srf.scan_report_table_id = {{ dag_run.conf["table_id"] }}
    ),
    matched_values AS (
        SELECT nv.id as new_value_id, ac.concept_id
        FROM new_values nv
        JOIN existing_values ev ON
            nv.value = ev.value AND
            nv.value_description = ev.value_description AND
            nv.field_name = ev.field_name
        JOIN active_concepts ac ON ev.id = ac.object_id
    )
    INSERT INTO scan_report_concepts (concept_id, content_type, object_id, source_type)
    SELECT
        mv.concept_id,
        'VALUE',
        mv.new_value_id,
        'R'
    FROM matched_values mv
    """,
    conn_id="postgres_default",
    dag=dag,
)

# Final status update
complete_reuse = SQLExecuteQueryOperator(
    task_id="complete_reuse",
    sql="""
    INSERT INTO job_statuses (table_id, stage, status, details, created_at)
    VALUES (
        {{ dag_run.conf["table_id"] }},
        'REUSE_CONCEPTS',
        'COMPLETE',
        'Finished',
        NOW()
    )
    """,
    conn_id="postgres_default",
    dag=dag,
)

(
    wait_for_creation
    >> start_reuse
    >> reuse_field_concepts
    >> update_field_reuse_status
    >> reuse_value_concepts
    >> complete_reuse
)

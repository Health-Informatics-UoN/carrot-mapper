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
    "concept_transformation",
    default_args=default_args,
    description="Transform scan report values to concepts",
    schedule_interval=None,
    catchup=False,
)

# Wait for vocabulary processing to complete
wait_for_vocab_processing = ExternalTaskSensor(
    task_id="wait_for_vocab_processing",
    external_dag_id="vocabulary_processing",
    external_task_id="add_vocabulary_ids",
    timeout=600,
    mode="reschedule",
    dag=dag,
)

# Process entries without vocabulary
process_null_vocabs = SQLExecuteQueryOperator(
    task_id="process_null_vocabs",
    sql="""
    UPDATE scan_report_values
    SET concept_id = -1, standard_concept = NULL
    WHERE vocabulary_id IS NULL
      AND scan_report_field_id IN (
        SELECT id FROM scan_report_fields
        WHERE scan_report_table_id = {{ dag_run.conf["table_id"] }}
      )
    """,
    conn_id="postgres_default",
    dag=dag,
)

# Match concepts for entries with vocabulary
match_concepts = SQLExecuteQueryOperator(
    task_id="match_concepts",
    sql="""
    WITH grouped_vocabs AS (
        SELECT DISTINCT vocabulary_id
        FROM scan_report_values
        WHERE vocabulary_id IS NOT NULL
          AND scan_report_field_id IN (
            SELECT id FROM scan_report_fields
            WHERE scan_report_table_id = {{ dag_run.conf["table_id"] }}
          )
    )
    INSERT INTO job_statuses (table_id, stage, status, details, created_at)
    SELECT
        {{ dag_run.conf["table_id"] }},
        'BUILD_CONCEPTS_FROM_DICT',
        'IN_PROGRESS',
        'Building concepts for ' || vocabulary_id || ' vocabulary',
        NOW()
    FROM grouped_vocabs
    """,
    conn_id="postgres_default",
    dag=dag,
)

# Find and apply concepts
find_concepts = SQLExecuteQueryOperator(
    task_id="find_concepts",
    sql="""
    UPDATE scan_report_values srv
    SET
        concept_id = c.concept_id,
        standard_concept = c.standard_concept
    FROM concepts c
    WHERE srv.vocabulary_id = c.vocabulary_id
      AND srv.value = c.concept_code
      AND srv.scan_report_field_id IN (
        SELECT id FROM scan_report_fields
        WHERE scan_report_table_id = {{ dag_run.conf["table_id"] }}
      )
    """,
    conn_id="postgres_default",
    dag=dag,
)

# Process non-standard concepts
process_nonstandard_concepts = SQLExecuteQueryOperator(
    task_id="process_nonstandard_concepts",
    sql="""
    WITH nonstandard_concepts AS (
        SELECT srv.id, srv.concept_id
        FROM scan_report_values srv
        WHERE srv.concept_id != -1
          AND srv.standard_concept != 'S'
          AND srv.scan_report_field_id IN (
            SELECT id FROM scan_report_fields
            WHERE scan_report_table_id = {{ dag_run.conf["table_id"] }}
          )
    ),
    standard_mappings AS (
        SELECT
            cr.concept_id_1 as nonstandard_concept_id,
            cr.concept_id_2 as standard_concept_id
        FROM concept_relationship cr
        JOIN nonstandard_concepts nc ON cr.concept_id_1 = nc.concept_id
        WHERE cr.relationship_id = 'Maps to'
          AND cr.invalid_reason IS NULL
    )
    UPDATE scan_report_values srv
    SET concept_id = sm.standard_concept_id
    FROM nonstandard_concepts nc
    JOIN standard_mappings sm ON nc.concept_id = sm.nonstandard_concept_id
    WHERE srv.id = nc.id
    """,
    conn_id="postgres_default",
    dag=dag,
)

(
    wait_for_vocab_processing
    >> process_null_vocabs
    >> match_concepts
    >> find_concepts
    >> process_nonstandard_concepts
)

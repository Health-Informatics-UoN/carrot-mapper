from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
import json
import ast

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 3, 25),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

dag = DAG(
    "concept_mapping_v0",
    default_args=default_args,
    description="Map scan report fields to standard concepts using SQL",
    schedule_interval=None,
    catchup=False,
)

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)


# Extract parameters
def extract_params(**kwargs):
    """Extract and validate parameters from DAG run configuration"""
    table_id = kwargs["dag_run"].conf.get("table_id")
    print("table_id: ", table_id)

    field_vocab_pairs = kwargs["dag_run"].conf.get("field_vocab_pairs")
    print("field_vocab_pairs: ", field_vocab_pairs, type(field_vocab_pairs))

    # Check if field_vocab_pairs is a string and try to parse it as JSON
    if isinstance(field_vocab_pairs, str):
        try:
            field_vocab_pairs = ast.literal_eval(field_vocab_pairs)
            print("Parsed field_vocab_pairs from string: ", field_vocab_pairs)
        except json.JSONDecodeError:
            print("Failed to parse field_vocab_pairs as JSON")

    if not table_id or not field_vocab_pairs or not isinstance(field_vocab_pairs, list):
        raise ValueError(
            f"Invalid parameters: requires table_id and field_vocab_pairs (as list). Got table_id={table_id}, field_vocab_pairs={field_vocab_pairs} of type {type(field_vocab_pairs)}"
        )

    # Get the first pair
    first_pair = field_vocab_pairs[0]
    sr_field_id = first_pair.get("sr_field_id")
    vocabulary_id = first_pair.get("vocabulary_id")

    if not sr_field_id or not vocabulary_id:
        raise ValueError(
            "Invalid field_vocab_pair: requires sr_field_id and vocabulary_id"
        )

    # Push to XCom for downstream tasks
    kwargs["ti"].xcom_push(key="table_id", value=table_id)
    kwargs["ti"].xcom_push(key="sr_field_id", value=sr_field_id)
    kwargs["ti"].xcom_push(key="vocabulary_id", value=vocabulary_id)

    return "Parameters successfully extracted"


extract_params_task = PythonOperator(
    task_id="extract_params",
    python_callable=extract_params,
    provide_context=True,
    dag=dag,
)

# Step 2: Find all values for each scan report field
get_sr_values = SQLExecuteQueryOperator(
    task_id="get_sr_values",
    sql="""
    -- Create a temporary table to store all values for the requested fields
    DROP TABLE IF EXISTS temp_sr_values;
    CREATE TABLE temp_sr_values AS
    SELECT
        srv.id AS sr_value_id,
        srv.value,
        srf.id AS sr_field_id,
        %(vocabulary_id)s AS vocabulary_id
    FROM mapping_scanreportvalue srv
    JOIN mapping_scanreportfield srf ON srv.scan_report_field_id = srf.id
    WHERE srf.scan_report_table_id = %(table_id)s
    AND srf.id = %(sr_field_id)s;
    """,
    conn_id="1-conn-db",
    parameters={
        "table_id": "{{ ti.xcom_pull(task_ids='extract_params', key='table_id') }}",
        "sr_field_id": "{{ ti.xcom_pull(task_ids='extract_params', key='sr_field_id') }}",
        "vocabulary_id": "{{ ti.xcom_pull(task_ids='extract_params', key='vocabulary_id') }}",
    },
    dag=dag,
)

# Step 3: Find non-standard concepts for each value
find_nonstandard_concepts = SQLExecuteQueryOperator(
    task_id="find_nonstandard_concepts",
    sql="""
    -- Find non-standard concepts for each value
    DROP TABLE IF EXISTS temp_nonstandard_concepts;
    CREATE TABLE temp_nonstandard_concepts AS
    SELECT
        tsv.sr_value_id,
        c.concept_id AS nonstandard_concept_id,
        c.standard_concept AS standard_concept
    FROM temp_sr_values tsv
    JOIN omop.concept c ON
        c.concept_code = tsv.value AND
        c.vocabulary_id = tsv.vocabulary_id;
    """,
    conn_id="1-conn-db",
    dag=dag,
)

# Step 4: Find standard concepts based on non-standard concepts
find_standard_concepts = SQLExecuteQueryOperator(
    task_id="find_standard_concepts",
    sql="""
    -- Find standard concepts mapped from non-standard concepts
    DROP TABLE IF EXISTS temp_standard_concepts;
    CREATE TABLE temp_standard_concepts AS
    SELECT
        tnc.sr_value_id,
        c.concept_id AS standard_concept_id
    FROM temp_nonstandard_concepts tnc
    JOIN omop.concept_relationship cr ON
        cr.concept_id_1 = tnc.nonstandard_concept_id AND
        cr.relationship_id = 'Maps to'
    JOIN omop.concept c ON
        c.concept_id = cr.concept_id_2 AND
        c.standard_concept = 'S';
    """,
    conn_id="1-conn-db",
    dag=dag,
)

# # Step 5: Create SR concepts using SQL
# create_sr_concepts = SQLExecuteQueryOperator(
#     task_id="create_sr_concepts",
#     sql="""
#     -- Insert standard concepts for field values
#     INSERT INTO mapping_scanreportconcept (
#         created_at,
#         updated_at,
#         object_id,
#         creation_type,
#         concept_id,
#         content_type_id
#     )
#     SELECT
#         NOW(),
#         NOW(),
#         tsc.sr_value_id,
#         'V',
#         tsc.standard_concept_id,
#         23
#     FROM temp_standard_concepts tsc
#     """,
#     conn_id="1-conn-db",
#     dag=dag,
# )

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

# TODO: what happens if users re-run these?


# WHERE NOT EXISTS (
#     -- Avoid duplicates
#     SELECT 1 FROM mapping_scanreportconcept src
#     WHERE src.object_id = tsc.sr_value_id::text
#     AND src.concept_id = tsc.standard_concept_id
#     AND src.content_type_id = 23
# );

# -- Get count of created concepts
# SELECT COUNT(*) as concepts_created FROM temp_standard_concepts;
# # Step 6: Mark the job as complete
# finish_job = SQLExecuteQueryOperator(
#     task_id="finish_job",
#     sql="""
#     UPDATE shared_jobs_job
#     SET
#         updated_at = NOW(),
#         status_id = (SELECT id FROM shared_jobs_stagestatus WHERE value = 'COMPLETE'),
#         details = CONCAT('Created ', (SELECT COUNT(*) FROM temp_standard_concepts), ' concepts based on field-vocabulary pairs')
#     WHERE
#         scan_report_table_id = %(table_id)s AND
#         stage_id = (SELECT id FROM shared_jobs_jobstage WHERE value = 'BUILD_CONCEPTS_FROM_DICT') AND
#         id = (
#             SELECT id FROM shared_jobs_job
#             WHERE scan_report_table_id = %(table_id)s AND
#             stage_id = (SELECT id FROM shared_jobs_jobstage WHERE value = 'BUILD_CONCEPTS_FROM_DICT')
#             ORDER BY created_at DESC LIMIT 1
#         );
#     """,
#     conn_id="1-conn-db",
#     parameters={"table_id": "{{ dag_run.conf['table_id'] }}"},
#     dag=dag,
# )

# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

# Define task dependencies
# (
#     start
#     >> start_job
#     >> get_sr_values
#     >> find_nonstandard_concepts
#     >> find_standard_concepts
#     >> create_sr_concepts
#     >> finish_job
#     >> end
# )

(
    start
    >> extract_params_task
    >> get_sr_values
    >> find_nonstandard_concepts
    >> find_standard_concepts
    >> end
)

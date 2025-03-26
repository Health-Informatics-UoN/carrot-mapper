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
    "concept_mapping_v2",
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

    field_vocab_pairs = kwargs["dag_run"].conf.get("field_vocab_pairs")

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

# Step 4: Find standard concepts based on non-standard concepts
find_standard_concepts = SQLExecuteQueryOperator(
    task_id="find_standard_concepts",
    sql="""
    -- Create final table with standard concepts directly
    -- This one will work if the 1 concpet have only 1 Maps to rel.
    DROP TABLE IF EXISTS temp_standard_concepts3;
    CREATE TABLE temp_standard_concepts3 AS
    SELECT
        srv.id AS sr_value_id,
        (
            SELECT c2.concept_id
            FROM omop.concept c2
            WHERE c2.concept_id IN (
                SELECT cr.concept_id_2
                FROM omop.concept_relationship cr
                WHERE cr.concept_id_1 IN (
                    SELECT c1.concept_id
                    FROM omop.concept c1
                    WHERE c1.concept_code = srv.value
                    AND c1.vocabulary_id = %(vocabulary_id)s
                )
                AND cr.relationship_id = 'Maps to'
            )
            AND c2.standard_concept = 'S'
            LIMIT 1
        ) AS standard_concept_id
    FROM mapping_scanreportvalue srv
    WHERE srv.scan_report_field_id = %(sr_field_id)s;
    DELETE FROM temp_standard_concepts3 WHERE standard_concept_id IS NULL;
    """,
    conn_id="1-conn-db",
    parameters={
        "table_id": "{{ ti.xcom_pull(task_ids='extract_params', key='table_id') }}",
        "sr_field_id": "{{ ti.xcom_pull(task_ids='extract_params', key='sr_field_id') }}",
        "vocabulary_id": "{{ ti.xcom_pull(task_ids='extract_params', key='vocabulary_id') }}",
    },
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


# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

(start >> extract_params_task >> find_standard_concepts >> end)

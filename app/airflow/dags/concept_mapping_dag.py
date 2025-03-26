from datetime import datetime
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
import json
import ast
from airflow.providers.postgres.hooks.postgres import PostgresHook

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="1-conn-db")

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 3, 25),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}

dag = DAG(
    "concept_mapping_v1",
    default_args=default_args,
    description="Map scan report fields to standard concepts using SQL",
    schedule_interval=None,
    catchup=False,
)


# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

# TODO: what happens if users re-run these?
# TODO: naming
# TODO: seperate Airflow schema


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

    for pair in field_vocab_pairs:

        sr_field_id = pair.get("sr_field_id")
        vocabulary_id = pair.get("vocabulary_id")

        if not sr_field_id or not vocabulary_id:
            raise ValueError(
                "Invalid field_vocab_pair: requires sr_field_id and vocabulary_id"
            )

        update_query = f"""
        DROP TABLE IF EXISTS temp_standard_concepts2;
        CREATE TABLE temp_standard_concepts2 AS
        SELECT
            srv.id AS sr_value_id,
            c2.concept_id AS standard_concept_id
        FROM mapping_scanreportvalue srv
        JOIN omop.concept c1 ON
            c1.concept_code = srv.value AND
            c1.vocabulary_id = '{vocabulary_id}'
        JOIN omop.concept_relationship cr ON
            cr.concept_id_1 = c1.concept_id AND
            cr.relationship_id = 'Maps to'
        JOIN omop.concept c2 ON
            c2.concept_id = cr.concept_id_2 AND
            c2.standard_concept = 'S'
        WHERE srv.scan_report_field_id = {sr_field_id};
        """

        pg_hook.run(update_query)

        create_concept_query = """
        -- Insert standard concepts for field values
        INSERT INTO mapping_scanreportconcept (
            created_at,
            updated_at,
            object_id,
            creation_type,
            concept_id,
            content_type_id
        )
        SELECT
            NOW(),
            NOW(),
            tsc.sr_value_id,
            'V',
            tsc.standard_concept_id,
            23
        FROM temp_standard_concepts2 tsc
        """

        pg_hook.run(create_concept_query)


extract_params_task = PythonOperator(
    task_id="extract_params",
    python_callable=extract_params,
    provide_context=True,
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

(start >> extract_params_task >> end)

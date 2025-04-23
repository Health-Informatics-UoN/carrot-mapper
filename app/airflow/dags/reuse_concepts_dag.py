from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from libs.core_reuse_concepts import (
    find_eligible_objects,
)

from libs.core_prep_rules_creation import (
    find_dest_table_and_person_field_id,
    find_date_fields,
    find_concept_fields,
    find_additional_fields,
)

from libs.core_rules_creation import (
    delete_mapping_rules,
    create_mapping_rules,
)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 3, 25),
    "email_on_failure": False,
    "email_on_retry": False,
    # TODO: modify these settings about retries
    "retries": 0,
}

dag = DAG(
    "reuse_concepts",
    default_args=default_args,
    description="""Find eligible objects for reuse concepts.
    After that, find the dest. table and OMOP field ids for each concept. 
    Eventually, create mapping rules for each reusing concept.""",
    tags=["R-concepts", "mapping_rules_creation"],
    schedule_interval=None,
    catchup=False,
)

# TODO: do we need to check AND NOT EXISTS? and when?
# TODO: many concepts have the domain "SPEC ANATOMIC SITE", which should be added to the table "SPECIMEN" in a different way (OMOP field id is different)
# TODO: ordering the temp standard concepts id before creating the mapping rules --> have the nice order match with the UI
# TODO: add dest field name to the UI??
# TODO: should we add `value` column in MAPPINGRULE model? in order to filter the mapping rule based on the SR value?
# TODO: add the source_concept_id to the UI
# TODO: improve naming of columns
# TODO: add docstrings to the functions

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)


find_eligible_objects_task = PythonOperator(
    task_id="find_eligible_objects",
    python_callable=find_eligible_objects,
    provide_context=True,
    dag=dag,
)


# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

(start >> find_eligible_objects_task >> end)

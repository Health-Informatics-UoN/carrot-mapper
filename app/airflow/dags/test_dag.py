from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from libs.core_concepts_creation import (
    find_standard_concepts,
    create_standard_concepts,
    find_sr_concept_id,
)

from libs.core_prep_rules_creation import (
    find_dest_table_and_person_field_id,
    find_date_fields,
    find_concept_fields,
    find_additional_fields,
)

from libs.core_test import (
    delete_mapping_rules,
    create_mapping_rules,
    temp_mapping_rules_table_creation,
    add_rules_to_temp_table,
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
    "create_concepts_from_vocab_dict",
    default_args=default_args,
    description="""Create standard concepts using vocabulary id from data dictionary for each scan report field. 
    After that, find the dest. table and OMOP field ids for each concept. 
    Eventually, create mapping rules for each scan report field.""",
    tags=["V-concepts", "mapping_rules_creation"],
    schedule_interval=None,
    catchup=False,
)

# TODO: do we need to check AND NOT EXISTS? and when?
# TODO: many concepts have the domain "SPEC ANATOMIC SITE", which should be added to the table "SPECIMEN" in a different way (OMOP field id is different)
# TODO: ordering the temp standard concepts id before creating the mapping rules --> have the nice order match with the UI
# TODO: add dest field name to the UI
# TODO: add tasks to do error handling and update status
# TODO: should we add `value` column in MAPPINGRULE model? in order to filter the mapping rule based on the SR value?
# TODO: add the source_concept_id to the UI
# TODO: improve naming of columns

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)


find_std_concepts_task = PythonOperator(
    task_id="find_standard_concepts",
    python_callable=find_standard_concepts,
    provide_context=True,
    dag=dag,
)


create_standard_concepts_task = PythonOperator(
    task_id="create_standard_concepts",
    python_callable=create_standard_concepts,
    provide_context=True,
    dag=dag,
)

find_sr_concept_id_task = PythonOperator(
    task_id="find_sr_concept_id",
    python_callable=find_sr_concept_id,
    provide_context=True,
    dag=dag,
)

find_dest_table_and_person_field_task = PythonOperator(
    task_id="find_dest_table_and_person_field_id",
    python_callable=find_dest_table_and_person_field_id,
    provide_context=True,
    dag=dag,
)

find_date_fields_task = PythonOperator(
    task_id="find_date_fields",
    python_callable=find_date_fields,
    provide_context=True,
    dag=dag,
)

find_concept_fields_task = PythonOperator(
    task_id="find_concept_fields",
    python_callable=find_concept_fields,
    provide_context=True,
    dag=dag,
)

find_additional_fields_task = PythonOperator(
    task_id="find_additional_fields",
    python_callable=find_additional_fields,
    provide_context=True,
    dag=dag,
)

delete_mapping_rules_task = PythonOperator(
    task_id="delete_mapping_rules",
    python_callable=delete_mapping_rules,
    provide_context=True,
    dag=dag,
)

create_mapping_rules_task = PythonOperator(
    task_id="create_mapping_rules",
    python_callable=create_mapping_rules,
    provide_context=True,
    dag=dag,
)

temp_mapping_rules_table_creation_task = PythonOperator(
    task_id="temp_mapping_rules_table_creation",
    python_callable=temp_mapping_rules_table_creation,
    provide_context=True,
    dag=dag,
)

temp_add_rules_to_temp_table_task = PythonOperator(
    task_id="add_rules_to_temp_table",
    python_callable=add_rules_to_temp_table,
    provide_context=True,
    dag=dag,
)

# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

(
    start
    >> find_std_concepts_task
    >> create_standard_concepts_task
    >> find_sr_concept_id_task
    >> find_dest_table_and_person_field_task
    >> find_date_fields_task
    >> find_concept_fields_task
    >> find_additional_fields_task
    >> delete_mapping_rules_task
    >> create_mapping_rules_task
    >> temp_mapping_rules_table_creation_task
    >> temp_add_rules_to_temp_table_task
    >> end
)

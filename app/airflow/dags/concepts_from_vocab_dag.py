from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from libs.core_create_concepts import (
    find_standard_concepts,
    create_standard_concepts,
    find_date_fields,
    find_additional_fields,
    find_concept_fields,
    find_dest_table_and_person_field_id,
)

from libs.core_rules_creation import (
    create_person_rules,
    create_dates_rules,
    create_concepts_rules,
    add_rules_to_temp_table,
    temp_mapping_rules_table_creation,
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
    description="Create standard concepts using vocabulary id from data dictionary for each scan report field. Also, find dest. table and OMOP field ids.",
    tags=["V-concepts"],
    schedule_interval=None,
    catchup=False,
)


# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)


find_std_concepts_task = PythonOperator(
    task_id="find_standard_concepts",
    python_callable=find_standard_concepts,
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

create_standard_concepts_task = PythonOperator(
    task_id="create_standard_concepts",
    python_callable=create_standard_concepts,
    provide_context=True,
    dag=dag,
)

temp_task_2 = PythonOperator(
    task_id="temp_mapping_rules_table_creation",
    python_callable=temp_mapping_rules_table_creation,
    provide_context=True,
    dag=dag,
)

temp_task = PythonOperator(
    task_id="add_rules_to_temp_table",
    python_callable=add_rules_to_temp_table,
    provide_context=True,
    dag=dag,
)

create_person_rules_task = PythonOperator(
    task_id="create_person_rules",
    python_callable=create_person_rules,
    provide_context=True,
    dag=dag,
)

create_dates_rules_task = PythonOperator(
    task_id="create_dates_rules",
    python_callable=create_dates_rules,
    provide_context=True,
    dag=dag,
)

create_concepts_rules_task = PythonOperator(
    task_id="create_concepts_rules",
    python_callable=create_concepts_rules,
    provide_context=True,
    dag=dag,
)
# TODO: add tasks to do error handling and update status


# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

(
    start
    >> find_std_concepts_task
    >> find_dest_table_and_person_field_task
    >> find_date_fields_task
    >> find_concept_fields_task
    >> find_additional_fields_task
    >> create_standard_concepts_task
    >> temp_task_2
    >> create_person_rules_task
    >> create_dates_rules_task
    >> create_concepts_rules_task
    >> temp_task
    >> end
)

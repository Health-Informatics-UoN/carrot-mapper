from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from libs.reuse_concepts.find_concepts_to_reuse import (
    create_temp_reusing_concepts_table,
    find_matching_field,
    find_matching_value,
    find_object_id,
    create_reusing_concepts,
    find_sr_concept_id,
)
from libs.reuse_concepts.prep_for_rules_creation import (
    find_dest_table_and_person_field_id,
    find_date_fields,
    find_concept_fields,
    find_additional_fields,
)
from libs.utils import create_task, validate_params_R_concepts

"""
This DAG automates the process of creating reusing concepts from other scan reports and then creating mapping rules accordingly.

Workflow steps:
1. Validate parameters
2. Find eligible objects for reuse concepts
3. Create temporary table to store reusing concepts
4. Find matching values for reusing concepts
5. Create reusing concepts in the database
6. Find scan report concept IDs
7. Find destination tables and person field IDs
8. Identify date fields, concept fields, and additional fields
9. Delete existing mapping rules
10. Create new mapping rules for each scan report field

"""
#  TODO: for now the creation of mapping rules will use the source_concept_id of temp_reuse_concepts table.
# When we can distinguish between standard and non-standard concepts, we will use them accordingly in the create_mapping_rules function of reuse.
# TODO: for death table, only reuse when the source table is death table as well
# TODO: update file names


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

# TODO: clean up

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

tasks = [
    create_task("validate_params_R_concepts", validate_params_R_concepts, dag),
    create_task(
        "create_temp_reusing_concepts_table", create_temp_reusing_concepts_table, dag
    ),
    create_task("find_matching_field", find_matching_field, dag),
    create_task("find_matching_value", find_matching_value, dag),
    create_task("find_object_id", find_object_id, dag),
    create_task("create_reusing_concepts", create_reusing_concepts, dag),
    create_task("find_sr_concept_id", find_sr_concept_id, dag),
    create_task(
        "find_dest_table_and_person_field_id", find_dest_table_and_person_field_id, dag
    ),
    create_task("find_date_fields", find_date_fields, dag),
    create_task("find_concept_fields", find_concept_fields, dag),
]


# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

# Execute the tasks
curr = start
for task in tasks:
    curr >> task
    curr = task
curr >> end

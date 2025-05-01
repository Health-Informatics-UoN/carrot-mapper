from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from libs.vocab_concepts.find_standard_concepts import (
    find_standard_concepts,
    create_standard_concepts,
    find_sr_concept_id,
)

from libs.vocab_concepts.prep_for_rules_creation import (
    find_dest_table_and_person_field_id,
    find_date_fields,
    find_concept_fields,
    find_additional_fields,
)

from libs.vocab_concepts.rules_creation import (
    delete_V_mapping_rules,
    create_mapping_rules,
)
from libs.utils import create_task, validate_params_V_concepts

"""
This DAG automates the process of creating standard concepts and mapping rules from vocabulary dictionaries.

Workflow steps:
1. Validate parameters
2. Find standard concepts using vocabulary IDs from data dictionaries
3. Create standard concepts in the database
4. Find scan report concept IDs
5. Find destination tables and person field IDs
6. Identify date fields, concept fields, and additional fields
7. Delete existing mapping rules
8. Create new mapping rules for each scan report field

"""


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

# TODO: orchestrator to be deleted because users will trigger this DAG directly. Similar for reuse DAG
# TODO: many concepts have the domain "SPEC ANATOMIC SITE", which should be added to the table "SPECIMEN" in a different way (OMOP field id is different)
# TODO: ordering the temp standard concepts id before creating the mapping rules --> have the nice order match with the UI
# TODO: should we add `value` column in MAPPINGRULE model? in order to filter the mapping rule based on the SR value?
# TODO: add the source_concept_id to the UI
# TODO: improve naming of columns
# TODO: add docstrings to the functions

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)


tasks = [
    create_task("validate_params_V_concepts", validate_params_V_concepts, dag),
    create_task("find_standard_concepts", find_standard_concepts, dag),
    create_task("create_standard_concepts", create_standard_concepts, dag),
    create_task("find_sr_concept_id", find_sr_concept_id, dag),
    create_task(
        "find_dest_table_and_person_field_id", find_dest_table_and_person_field_id, dag
    ),
    create_task("find_date_fields", find_date_fields, dag),
    create_task("find_concept_fields", find_concept_fields, dag),
    create_task("find_additional_fields", find_additional_fields, dag),
    create_task("delete_mapping_rules", delete_V_mapping_rules, dag),
    create_task("create_mapping_rules", create_mapping_rules, dag),
]


# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

# Execute the tasks
curr = start
for task in tasks:
    curr >> task
    curr = task
curr >> end

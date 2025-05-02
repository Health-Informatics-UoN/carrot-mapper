from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from libs.find_concepts_to_reuse import (
    find_matching_field,
    find_matching_value,
    find_object_id,
    create_reusing_concepts,
    delete_R_concepts,
)

from libs.find_standard_concepts import (
    find_standard_concepts,
    create_standard_concepts,
)

from libs.core_get_existing_concepts import (
    delete_mapping_rules,
    create_temp_existing_concepts_table,
    find_existing_concepts,
)
from libs.core_prep_rules_creation import (
    find_dest_table_and_person_field_id,
    find_date_fields,
    find_concept_fields,
    find_additional_fields,
)
from libs.core_rules_creation import create_mapping_rules
from libs.utils import create_task, validate_params

"""
This DAG automates the process of creating and reusing concepts from scan reports and generating mapping rules.

Workflow steps:
1. Validate input parameters
2. Delete existing mapping rules
3. Find and create standard concepts (V-concepts)
4. Delete existing reusable concepts (R-concepts)
5. Find matching values, fields, and object IDs for reuse
6. Create reusable concepts based on matches
7. Create temporary tables of existing concepts
8. Collect all existing concepts
9. Identify destination tables and person field IDs
10. Find date fields for each concept
11. Find concept fields for mapping
12. Find additional fields needed for mapping
13. Create mapping rules based on all collected information

This pipeline enables efficient concept reuse across scan reports and automates the creation of
mapping rules connecting source data to OMOP-compliant destination tables.
"""
#  TODO: for now the creation of mapping rules will use the source_concept_id of temp_reuse_concepts table.
# When we can distinguish between standard and non-standard concepts, we will use them accordingly in the create_mapping_rules function of reuse.
# TODO: for death table, only reuse when the source table is death table as well
# TODO: compare the R and V logic related to prep_for_rules_creation
# TODO: do we want to reuse R concepts?
# NOTE: when the DB is huge, the performance of the DAG will be affected by refreshing the existing R concepts. --> consider to only refresh the R Mapping rules
# TODO: many concepts have the domain "SPEC ANATOMIC SITE", which should be added to the table "SPECIMEN" in a different way (OMOP field id is different)
# TODO: should we add `value` column in MAPPINGRULE model? in order to filter the mapping rule based on the SR value?
# TODO: add the source_concept_id to the UI
# TODO: improve naming of columns

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
    "auto_mapping",
    default_args=default_args,
    description="""Find and create V and R concepts. Then get all the existing concepts, 
    and find the dest. table and OMOP field ids for each concept.
    After that, create mapping rules for each concept.""",
    tags=["V-concepts", "R-concepts", "mapping_rules_creation"],
    schedule_interval=None,
    catchup=False,
)

# TODO: clean up

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

tasks = [
    create_task("validate_params", validate_params, dag),
    create_task("delete_mapping_rules", delete_mapping_rules, dag),
    create_task("find_standard_concepts", find_standard_concepts, dag),
    create_task("create_standard_concepts", create_standard_concepts, dag),
    create_task("delete_R_concepts", delete_R_concepts, dag),
    create_task("find_matching_value", find_matching_value, dag),
    create_task("find_matching_field", find_matching_field, dag),
    create_task("find_object_id", find_object_id, dag),
    create_task("create_reusing_concepts", create_reusing_concepts, dag),
    create_task(
        "create_temp_existing_concepts_table", create_temp_existing_concepts_table, dag
    ),
    create_task("find_existing_concepts", find_existing_concepts, dag),
    create_task(
        "find_dest_table_and_person_field_id",
        find_dest_table_and_person_field_id,
        dag,
    ),
    create_task("find_date_fields", find_date_fields, dag),
    create_task("find_concept_fields", find_concept_fields, dag),
    create_task("find_additional_fields", find_additional_fields, dag),
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

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from libs.auto_mapping.find_R_concepts_to_reuse import (
    find_matching_field,
    find_matching_value,
    create_reusing_concepts,
    delete_R_concepts,
)

from libs.auto_mapping.find_standard_V_concepts import (
    find_standard_concepts,
    create_standard_concepts,
)

from libs.auto_mapping.core_get_existing_concepts import (
    delete_mapping_rules,
    find_existing_concepts,
)
from libs.auto_mapping.core_prep_rules_creation import (
    find_dest_table_and_person_field_id,
    find_date_fields,
    find_concept_fields,
    find_additional_fields,
)
from libs.auto_mapping.core_rules_creation import create_mapping_rules
from libs.auto_mapping.search_recommendations import process_search_recommendations
from libs.utils import create_task, validate_params_auto_mapping
from libs.settings import AIRFLOW_DEBUG_MODE, SEARCH_ENABLED, AIRFLOW_DAGRUN_TIMEOUT

"""
This DAG automates the process of creating and reusing concepts from scan reports and generating mapping rules.

Workflow steps:
1. Validate input parameters
2. Delete existing mapping rules
3. Find and create standard concepts (V-concepts)
4. Delete existing reusable concepts (R-concepts)
5. Find matching values, fields, and object IDs for reuse
6. Create reusable concepts based on matches
7. Collect all existing concepts
8. Identify destination tables and person field IDs
9. Find date fields for each concept
10. Find concept fields for mapping
11. Find additional fields needed for mapping
12. Create mapping rules based on all collected information
13. (Optional) Generate search-based recommendations when SEARCH_ENABLED=true

This pipeline enables efficient concept reuse across scan reports and automates the creation of
mapping rules connecting source data to OMOP-compliant destination tables.
"""
#  TODO: for now the creation of mapping rules will use the source_concept_id of temp_reuse_concepts table.
# When we can distinguish between standard and non-standard concepts, we will use them accordingly in the create_mapping_rules function of reuse.
# TODO: for death table, only reuse when the source table is death table as well
# NOTE: when the DB is huge, the performance of the DAG will be affected by refreshing the existing R concepts. --> consider to only refresh the R Mapping rules
# TODO: should we add `value` column in MAPPINGRULE model? in order to filter the mapping rule based on the SR value?
# TODO: add the source_concept_id to the UI
# TODO: improve naming of columns

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 3, 25),
    # TODO: add email on failure and retry
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0 if AIRFLOW_DEBUG_MODE == "true" else 3,
    "retry_delay": timedelta(minutes=1),
}

dag = DAG(
    "auto_mapping",
    default_args=default_args,
    description="""Find and create V and R concepts. Then get all the existing concepts, 
    and find the dest. table and OMOP field ids for each concept.
    After that, create mapping rules for each concept.
    Optionally includes search-based recommendations when SEARCH_ENABLED=true.""",
    tags=[
        "V-concepts",
        "R-concepts",
        "mapping_rules_creation",
        "search_recommendations",
    ],
    schedule_interval=None,
    catchup=False,
    is_paused_upon_creation=False,
    dagrun_timeout=timedelta(minutes=float(AIRFLOW_DAGRUN_TIMEOUT)),
)

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

tasks = [
    create_task("validate_params_auto_mapping", validate_params_auto_mapping, dag),
    create_task("delete_mapping_rules", delete_mapping_rules, dag),
    create_task("find_standard_concepts", find_standard_concepts, dag),
    create_task("create_standard_concepts", create_standard_concepts, dag),
    create_task("delete_R_concepts", delete_R_concepts, dag),
    create_task("find_matching_value", find_matching_value, dag),
    create_task("find_matching_field", find_matching_field, dag),
    create_task("create_reusing_concepts", create_reusing_concepts, dag),
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

# Conditionally add search recommendations task
if SEARCH_ENABLED == "true":
    tasks.append(
        create_task(
            "process_search_recommendations", process_search_recommendations, dag
        )
    )

# End the workflow
end = EmptyOperator(task_id="end", dag=dag)

# Execute the tasks
curr = start
for task in tasks:
    curr >> task
    curr = task
curr >> end

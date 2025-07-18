from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
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
from libs.utils import create_task, validate_params_auto_mapping
from libs.settings import AIRFLOW_DEBUG_MODE, SEARCH_ENABLED

"""
This DAG extends the auto_mapping workflow to include search recommendations as a downstream dependency.

This DAG combines the standard auto-mapping process with search-based recommendations,
providing a comprehensive mapping solution that includes both vocabulary-based and string-search-based
concept matching. The search recommendations task is conditionally added based on the SEARCH_ENABLED environment variable.
"""

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 3, 25),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0 if AIRFLOW_DEBUG_MODE == "true" else 3,
    "retry_delay": timedelta(minutes=1),
}

dag = DAG(
    "auto_mapping_with_search",
    default_args=default_args,
    description="""
    Extended auto-mapping DAG that includes search-based recommendations.
    This combines vocabulary-based concept mapping with string-search-based recommendations
    for comprehensive concept discovery and mapping.
    """,
    tags=["auto_mapping", "search_recommendations", "mapping"],
    schedule_interval=None,
    catchup=False,
    is_paused_upon_creation=False,
)

# Start the workflow
start = EmptyOperator(task_id="start", dag=dag)

# Auto mapping tasks (same as auto_mapping_dag.py)
auto_mapping_tasks = [
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

# Execute auto mapping tasks
curr = start
for task in auto_mapping_tasks:
    curr >> task
    curr = task

# Conditionally add search recommendations trigger
if SEARCH_ENABLED == "true":
    # Trigger the search_recommendations DAG with the same parameters
    trigger_search = TriggerDagRunOperator(
        task_id="trigger_search_recommendations",
        trigger_dag_id="search_recommendations",
        conf={
            "scan_report_id": "{{ dag_run.conf.scan_report_id }}",
            "table_id": "{{ dag_run.conf.table_id }}",
        },
        dag=dag,
    )

    # Chain the search trigger after auto mapping
    curr >> trigger_search
    curr = trigger_search

# End the workflow
end = EmptyOperator(task_id="end", dag=dag)
curr >> end

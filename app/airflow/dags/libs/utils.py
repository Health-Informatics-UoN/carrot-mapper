import logging
import ast
import json
from airflow.providers.postgres.hooks.postgres import PostgresHook
from enum import Enum
from airflow.operators.python import PythonOperator
from typing import TypedDict, List, Optional


# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


# Define a type for field-vocab pairs
class FieldVocabPair(TypedDict):
    sr_field_id: int
    field_data_type: str
    vocabulary_id: str


# Define a type for validated parameters
class ValidatedParams(TypedDict):
    scan_report_id: int
    table_id: int
    person_id_field: int
    date_event_field: int
    field_vocab_pairs: List[FieldVocabPair]
    parent_dataset_id: Optional[int]
    has_data_dictionary: Optional[bool]


class StageStatusType(Enum):
    IN_PROGRESS = "Job in Progress"
    COMPLETE = "Job Complete"
    FAILED = "Job Failed"


class JobStageType(Enum):
    UPLOAD_SCAN_REPORT = "Upload Scan Report"
    BUILD_CONCEPTS_FROM_DICT = "Build concepts from OMOP Data dictionary"
    REUSE_CONCEPTS = "Reuse concepts from other scan reports"
    GENERATE_RULES = "Generate mapping rules from available concepts"
    DOWNLOAD_RULES = "Generate and download mapping rules JSON"


def _process_field_vocab_pairs(field_vocab_pairs: str):
    """Extract and validate field_vocab_pairs from DAG run configuration"""

    # Check if field_vocab_pairs is a string and try to parse it as JSON
    if isinstance(field_vocab_pairs, str):
        try:
            field_vocab_pairs = ast.literal_eval(field_vocab_pairs)
        except json.JSONDecodeError:
            logging.error("Failed to parse field_vocab_pairs as JSON")
            raise ValueError("Failed to parse field_vocab_pairs as JSON")

    return field_vocab_pairs


def update_job_status(
    scan_report: int,
    scan_report_table: int,
    stage: JobStageType,
    status: StageStatusType,
    details: str = "",
) -> None:
    """Update the status of a job in the database"""
    # TODO: for upload SR, this fuction will update the SR record in mapping_scanreport, not the job record
    update_query = f"""
        UPDATE jobs_job
        SET status_id = (
            SELECT id FROM jobs_stagestatus WHERE value = '{status.name}'
        ),
        details = '{details}', 
        updated_at = NOW()
        WHERE id = (
            SELECT id FROM jobs_job
            WHERE scan_report_id = {scan_report}
            AND scan_report_table_id = {scan_report_table}
            AND stage_id IN (
                SELECT id FROM jobs_jobstage WHERE value = '{stage.name}'
            )
            ORDER BY updated_at DESC
            LIMIT 1
        )
    """
    pg_hook.run(update_query)


def create_task(task_id, python_callable, dag, provide_context=True):
    """Create a task in the DAG"""
    return PythonOperator(
        task_id=task_id,
        python_callable=python_callable,
        provide_context=provide_context,
        dag=dag,
    )


def _validate_params(
    context,
    int_params: list,
    require_field_vocab_pairs: bool = False,
    require_has_data_dictionary: bool = False,
) -> dict:
    """
    Generic parameter validation for DAG tasks.
    """
    conf = context["dag_run"].conf
    errors = []
    validated_params = {}

    # Validate and convert integer parameters
    for param in int_params:
        value = conf.get(param)
        print(f"value: {value}")
        if value is None:
            errors.append(f"Missing required parameter: {param}")
            continue
        try:
            validated_params[param] = int(value)
        except (ValueError, TypeError):
            errors.append(f"Invalid {param}: {value}. Must be an integer.")

    # Optionally validate field_vocab_pairs
    if require_field_vocab_pairs:
        field_vocab_pairs = conf.get("field_vocab_pairs")
        if not field_vocab_pairs:
            errors.append("Missing required parameter: field_vocab_pairs")
        else:
            validated_params["field_vocab_pairs"] = _process_field_vocab_pairs(
                field_vocab_pairs
            )

    # Optionally validate has_data_dictionary as boolean
    if require_has_data_dictionary:
        has_data_dictionary = conf.get("has_data_dictionary")
        if has_data_dictionary is None:
            errors.append("Missing required parameter: has_data_dictionary")
        elif isinstance(has_data_dictionary, str):
            if has_data_dictionary.lower() in ["true", "false"]:
                validated_params["has_data_dictionary"] = bool(
                    has_data_dictionary.lower()
                )
            else:
                errors.append(
                    f"Invalid has_data_dictionary: {has_data_dictionary}. Must be a boolean (true/false)."
                )
        elif isinstance(has_data_dictionary, bool):
            validated_params["has_data_dictionary"] = has_data_dictionary
        else:
            errors.append(
                f"Invalid has_data_dictionary: {has_data_dictionary}. Must be a boolean."
            )

    if errors:
        error_message = "Parameter validation failed: " + "; ".join(errors)
        logging.error(error_message)
        raise ValueError(error_message)

    return validated_params


def validate_params_V_concepts(**context):
    return _validate_params(
        context,
        int_params=[
            "table_id",
            "person_id_field",
            "date_event_field",
            "scan_report_id",
        ],
        require_field_vocab_pairs=True,
    )


def validate_params_R_concepts(**context):
    return _validate_params(
        context,
        int_params=[
            "table_id",
            "person_id_field",
            "date_event_field",
            "scan_report_id",
            "parent_dataset_id",
        ],
        require_field_vocab_pairs=False,
        require_has_data_dictionary=True,
    )


def pull_validated_params(kwargs: dict, task_id: str) -> ValidatedParams:
    """Pull parameters from XCom for a given task"""
    task_instance = kwargs["ti"]
    return task_instance.xcom_pull(task_ids=task_id)

import logging
import ast
import json
from airflow.providers.postgres.hooks.postgres import PostgresHook
from enum import Enum
from airflow.operators.python import PythonOperator
from typing import TypedDict, List, Optional, Any, Dict
from airflow.providers.microsoft.azure.hooks.wasb import WasbHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.models.connection import Connection
from airflow.utils.session import create_session
from libs.enums import StorageType
import os

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
    parent_dataset_id: int
    trigger_reuse_concepts: bool


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
    status_value = status.name
    stage_value = stage.name

    update_query = """
        UPDATE jobs_job
        SET status_id = (
            SELECT id FROM jobs_stagestatus WHERE value = %(status_value)s
        ),
        details = %(details)s, 
        updated_at = NOW()
        WHERE id = (
            SELECT id FROM jobs_job
            WHERE scan_report_id = %(scan_report)s
            AND scan_report_table_id = %(scan_report_table)s
            AND stage_id IN (
                SELECT id FROM jobs_jobstage WHERE value = %(stage_value)s
            )
            ORDER BY updated_at DESC
            LIMIT 1
        )
    """
    try:
        pg_hook.run(
            update_query,
            parameters={
                "scan_report": scan_report,
                "scan_report_table": scan_report_table,
                "status_value": status_value,
                "details": details,
                "stage_value": stage_value,
            },
        )
    except Exception as e:
        logging.error(f"Error in update_job_status: {str(e)}")
        raise ValueError(f"Error in update_job_status: {str(e)}")


def create_task(task_id, python_callable, dag, provide_context=True):
    """Create a task in the DAG"""
    return PythonOperator(
        task_id=task_id,
        python_callable=python_callable,
        provide_context=provide_context,
        dag=dag,
    )


def _validate_dag_params(
    int_params=None,
    string_params=None,
    bool_params=None,
    has_field_vocab_pairs=False,
    **context,
):
    """
    Unified parameter validation for DAG tasks.

    Args:
        int_params: List of integer parameter names to validate
        string_params: List of string parameter names to validate
        bool_params: List of boolean parameter names to validate
        field_vocab_pairs: Whether to validate field_vocab_pairs parameter
        context: Airflow context dictionary

    Returns:
        Dictionary of validated parameters
    """
    conf = context["dag_run"].conf
    errors = []
    validated_params = {}

    # Validate and convert integer parameters
    if int_params:
        for param in int_params:
            value = conf.get(param)
            if value is None:
                errors.append(f"Missing required parameter: {param}")
                continue
            try:
                validated_params[param] = int(value)
            except (ValueError, TypeError):
                errors.append(f"Invalid {param}: {value}. Must be an integer.")

    # Validate and convert string parameters
    if string_params:
        for param in string_params:
            value = conf.get(param)
            if value is None or value.strip() == "":
                errors.append(f"Missing required parameter: {param}")
                continue
            validated_params[param] = value

    # Validate boolean parameters
    if bool_params:
        for param in bool_params:
            value = conf.get(param)
            if value is None:
                errors.append(f"Missing required parameter: {param}")
            elif isinstance(value, str):
                if value.lower() in ["true", "false"]:
                    validated_params[param] = bool(value.lower())
                else:
                    errors.append(
                        f"Invalid {param}: {value}. Must be a boolean (true/false)."
                    )
            elif isinstance(value, bool):
                validated_params[param] = value
            else:
                errors.append(f"Invalid {param}: {value}. Must be a boolean.")

    # Validate field_vocab_pairs
    if has_field_vocab_pairs:
        field_vocab_pairs = conf.get("field_vocab_pairs")
        if not field_vocab_pairs:
            validated_params["field_vocab_pairs"] = []
        else:
            validated_params["field_vocab_pairs"] = _process_field_vocab_pairs(
                field_vocab_pairs
            )

    # Raise error if any validation failed
    if errors:
        error_message = "Parameter validation failed: " + "; ".join(errors)
        logging.error(error_message)
        raise ValueError(error_message)

    return validated_params


# Define convenience functions for specific validation scenarios
def validate_params_auto_mapping(**context):
    """Validates parameters required for auto mapping DAG tasks."""
    int_params = [
        "scan_report_id",
        "table_id",
        "person_id_field",
        "date_event_field",
        "parent_dataset_id",
    ]
    bool_params = ["trigger_reuse_concepts"]
    return _validate_dag_params(
        int_params=int_params,
        bool_params=bool_params,
        has_field_vocab_pairs=True,
        **context,
    )


def validate_params_SR_processing(**context):
    """Validates parameters required for scan report processing DAG tasks."""
    int_params = ["scan_report_id"]
    string_params = ["scan_report_blob", "data_dictionary_blob"]
    return _validate_dag_params(
        int_params=int_params, string_params=string_params, **context
    )


def pull_validated_params(kwargs: dict, task_id: str) -> ValidatedParams:
    """Pull parameters from XCom for a given task"""
    task_instance = kwargs["ti"]
    return task_instance.xcom_pull(task_ids=task_id)


storage_type = os.getenv("STORAGE_TYPE", StorageType.MINIO)


def connect_to_storage():
    with create_session() as session:
        if storage_type == StorageType.AZURE:
            # Check if WASB connection exists
            existing_conn = (
                session.query(Connection)
                .filter(Connection.conn_id == "wasb_conn")
                .first()
            )

            if existing_conn is None:
                conn = Connection(
                    conn_id="wasb_conn",
                    conn_type="wasb",
                    extra={
                        "connection_string": os.getenv(
                            "AIRFLOW_VAR_WASB_CONNECTION_STRING"
                        ),
                    },
                )
                session.add(conn)
                session.commit()
                logging.info("Created new WASB connection")

        elif storage_type == StorageType.MINIO:
            # Check if MinIO connection exists
            existing_conn = (
                session.query(Connection)
                .filter(Connection.conn_id == "minio_conn")
                .first()
            )

            if existing_conn is None:
                conn = Connection(
                    conn_id="minio_conn",
                    conn_type="aws",
                    extra={
                        "endpoint_url": os.getenv("AIRFLOW_VAR_MINIO_ENDPOINT"),
                        "aws_access_key_id": os.getenv("AIRFLOW_VAR_MINIO_ACCESS_KEY"),
                        "aws_secret_access_key": os.getenv(
                            "AIRFLOW_VAR_MINIO_SECRET_KEY"
                        ),
                    },
                )
                session.add(conn)
                session.commit()
                logging.info("Created new MinIO connection")


def get_storage_hook():
    if storage_type == StorageType.AZURE:
        return WasbHook(wasb_conn_id="wasb_conn")
    elif storage_type == StorageType.MINIO:
        return S3Hook(aws_conn_id="minio_conn")
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


def remove_BOM(intermediate: List[Dict[str, Any]]):
    """
    Given a list of dictionaries, remove any occurrences of the BOM in the keys.

    Args:
        intermediate (List[Dict[str, Any]]): List of dictionaries to remove from.

    Returns:
        The list of dictionaries with BOM removed from the keys.
    """
    return [
        {key.replace("\ufeff", ""): value for key, value in d.items()}
        for d in intermediate
    ]


def process_four_item_dict(four_item_data):
    """
    Converts a list of dictionaries (each with keys 'csv_file_name', 'field_name' and
    'code' and 'value') to a nested dictionary with indices 'csv_file_name',
    'field_name', 'code', and internal value 'value'.

    [{'csv_file_name': 'table1', 'field_name': 'field1', 'value': 'value1', 'code':
    'code1'},
    {'csv_file_name': 'table1', 'field_name': 'field2', 'value': 'value2', 'code':
    'code2'},
    {'csv_file_name': 'table2', 'field_name': 'field2', 'value': 'value2', 'code':
    'code2'},
    {'csv_file_name': 'table2', 'field_name': 'field2', 'value': 'value3', 'code':
    'code3'},
    {'csv_file_name': 'table3', 'field_name': 'field3', 'value': 'value3', 'code':
    'code3'}]
    ->
    {'table1': {'field1': {'value1': 'code1'}, 'field2': {'value2': 'code2'}},
    'table2': {'field2': {'value2': 'code2', 'value3': 'code3'}},
    'table3': {'field3': {'value3': 'code3'}}
    }
    """
    csv_file_names = set(row["csv_file_name"] for row in four_item_data)

    # Initialise the dictionary with the keys, and each value set to a blank dict()
    new_data_dictionary = dict.fromkeys(csv_file_names, {})

    for row in four_item_data:
        if row["field_name"] not in new_data_dictionary[row["csv_file_name"]]:
            new_data_dictionary[row["csv_file_name"]][row["field_name"]] = {}
        new_data_dictionary[row["csv_file_name"]][row["field_name"]][row["code"]] = row[
            "value"
        ]

    return new_data_dictionary

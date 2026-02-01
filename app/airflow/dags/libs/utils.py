import ast
import json
import logging
import multiprocessing
import time
from typing import Any, Dict, List, Optional, TypedDict

from airflow.models.connection import Connection
from airflow.models.taskinstance import TaskInstance
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.session import create_session

from libs.enums import JobStageType, StageStatusType, StorageType
from libs.settings import (
    AIRFLOW_DAGRUN_TIMEOUT,
    AIRFLOW_VAR_MINIO_ACCESS_KEY,
    AIRFLOW_VAR_MINIO_ENDPOINT,
    AIRFLOW_VAR_MINIO_SECRET_KEY,
    AIRFLOW_VAR_WASB_CONNECTION_STRING,
    TEMP_TABLE_CLEANUP_DELAY,
    storage_type,
)

# PostgreSQL connection hook
pg_hook = PostgresHook(
    postgres_conn_id="postgres_db_conn",
    options=f"-c statement_timeout={float(AIRFLOW_DAGRUN_TIMEOUT) * 60 * 1000}ms",
)


# Define a type for field-vocab pairs
class FieldVocabPair(TypedDict):
    sr_field_id: int
    field_data_type: str
    vocabulary_id: str


# Define a type for validated parameters
class ValidatedParams(TypedDict):
    scan_report_id: int
    scan_report_name: str
    table_id: int
    person_id_field: int
    date_event_field: int
    field_vocab_pairs: List[FieldVocabPair]
    parent_dataset_id: int
    trigger_reuse_concepts: bool
    scan_report_blob: str
    data_dictionary_blob: Optional[str]
    user_id: int
    file_type: str


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
    stage: JobStageType,
    status: StageStatusType,
    scan_report: int,
    scan_report_table: Optional[int] = None,
    details: str = "",
) -> None:
    """
    Update the status of a job in the database.

    Args:
        stage (JobStageType): The stage of the job (e.g., UPLOAD_SCAN_REPORT, DOWNLOAD_RULES)
        status (StageStatusType): The status to set
        scan_report (int): ID of the scan report
        scan_report_table (Optional[int]): ID of the scan report table (if applicable)
        details (str): Additional details about the status update

    Raises:
        ValueError: If there's an error updating the job status
    """
    # Base parameters used in all queries
    params: Dict[str, Any] = {
        "scan_report": scan_report,
        "status_value": status.name,
        "stage_value": stage.name,
        "details": details,
    }

    # Define query templates
    update_sr_job_query = """
        UPDATE mapping_scanreport
        SET upload_status_id = (
            SELECT id FROM mapping_uploadstatus 
            WHERE value = %(status_value)s
        ),
        upload_status_details = %(details)s
        WHERE id = %(scan_report)s
    """

    job_update_query = """
        UPDATE jobs_job
        SET status_id = (
            SELECT id FROM jobs_stagestatus 
            WHERE value = %(status_value)s
        ),
        details = %(details)s,
        updated_at = NOW()
        WHERE id = (
            SELECT id FROM jobs_job
            WHERE scan_report_id = %(scan_report)s
            {additional_conditions}
            AND stage_id IN (
                SELECT id FROM jobs_jobstage 
                WHERE value = %(stage_value)s
            )
            ORDER BY updated_at DESC
            LIMIT 1
        )
    """

    try:
        if stage == JobStageType.UPLOAD_SCAN_REPORT:
            update_query = update_sr_job_query
        else:
            # Add scan_report_table condition if needed
            additional_conditions = ""
            if stage != JobStageType.DOWNLOAD_RULES:
                additional_conditions = (
                    "AND scan_report_table_id = %(scan_report_table)s"
                )
                params["scan_report_table"] = scan_report_table

            update_query = job_update_query.format(
                additional_conditions=additional_conditions
            )

        pg_hook.run(update_query, parameters=params)

    except Exception:
        error_msg = f"Failed to update job status for scan_report={scan_report}, stage={stage.name}"
        logging.error(error_msg)
        raise ValueError(error_msg)


def update_job_status_on_failure(context):
    """
    Update job status on skipped task.

    This function is designed to be used as an Airflow callback that receives the
    execution context. It extracts the scan_report_id from the DAG run configuration
    and updates the job status to FAILED with appropriate stage information.

    Args:
        context: Airflow execution context containing task_instance, dag, dag_run, etc.
    """
    logging.info("update_job_status_on_failure callback triggered")
    try:
        # Extract information from Airflow context
        task_instance = context["task_instance"]
        dag = context["dag"]
        dag_run = context["dag_run"]

        # Determine the appropriate stage based on DAG ID and task ID
        if dag.dag_id == "rules_export":
            stage = JobStageType.DOWNLOAD_RULES
        elif dag.dag_id == "auto_mapping":
            # For auto_mapping DAG, determine stage based on task name
            task_id = task_instance.task_id
            if task_id in [
                "delete_mapping_rules",
                "find_standard_concepts",
                "create_standard_concepts",
            ]:
                stage = JobStageType.BUILD_CONCEPTS_FROM_DICT
            elif task_id in [
                "find_matching_value",
                "find_matching_field",
                "create_reusing_concepts",
                "delete_R_concepts",
            ]:
                stage = JobStageType.REUSE_CONCEPTS
            else:
                stage = JobStageType.GENERATE_RULES
        else:
            logging.error(f"No job stage found for {dag.dag_id}.")
            return

        # Extract scan_report_id from DAG run configuration
        dag_run_conf = dag_run.conf or {}
        scan_report_id = dag_run_conf.get("scan_report_id")

        if not scan_report_id:
            logging.error(
                f"No scan_report_id found in DAG run configuration for {dag.dag_id}"
            )
            return

        # Get table_id if available (needed for some stages)
        table_id = dag_run_conf.get("table_id")
        # Update job status as failed
        update_job_status(
            stage=stage,
            status=StageStatusType.FAILED,
            scan_report=scan_report_id,
            scan_report_table=table_id,
            details=f"Task '{task_instance.task_id}' was timed-out or failed due to an unexpected error.",
        )

    except Exception as e:
        logging.error(f"Failed to update job status on skipped task: {str(e)}")


def handle_failure_and_cleanup_temp_tables(context):
    """
    Delete temporary tables when the DAG fails or times out.

    This handles cleanup when failures happen outside the normal pipeline code, like
    timeouts or external errors. Since the tables are already in the database even if
    the DAG fails, we query mapping_scanreporttable to find all tables for this
    scan_report_id, then delete the temp tables (temp_data_dictionary and
    temp_field_values).

    When a timeout occurs, the task that was running may still be creating temporary tables in the background.
    This function waits TEMP_TABLE_CLEANUP_DELAY seconds first so any in-flight table creation can finish,
    then runs a single cleanup pass. Cleanup is not urgent, so waiting once is simpler than cleaning twice.


    Args:
        context: Airflow execution context containing task_instance, dag, dag_run, etc.
    """
    try:
        dag_run = context["dag_run"]
        dag = context.get("dag")
        dag_run_conf = dag_run.conf or {}
        scan_report_id = dag_run_conf.get("scan_report_id")

        if not scan_report_id:
            logging.warning(
                "No scan_report_id found in DAG run configuration, skipping temp table cleanup"
            )
            return

        # Update job status to FAILED for scan_report_processing DAG
        if dag and dag.dag_id == "scan_report_processing":
            try:
                update_job_status(
                    stage=JobStageType.UPLOAD_SCAN_REPORT,
                    status=StageStatusType.FAILED,
                    scan_report=scan_report_id,
                    details="Scan report processing DAG timed out or failed.",
                )
                logging.info(
                    "Updated job status to FAILED for scan_report_id=%s",
                    scan_report_id,
                )
            except Exception as e:
                logging.error("Failed to update job status on failure: %s", str(e))

        # Wait so a timed-out task can finish creating tables, then delete the temporary tables
        delay = TEMP_TABLE_CLEANUP_DELAY
        time.sleep(delay)

        # I did this to avoid circular import
        from libs.SR_processing.db_services import cleanup_temp_tables_for_scan_report

        table_pairs = cleanup_temp_tables_for_scan_report(scan_report_id)
        if table_pairs:
            logging.info(
                "Deleted temp tables for scan_report_id=%s (n=%d)",
                scan_report_id,
                len(table_pairs),
            )
        logging.info(
            "Completed temp table cleanup for scan_report_id=%s", scan_report_id
        )

    except Exception as e:
        logging.error("Failed to delete temporary tables on failure: %s", str(e))


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
    check_data_dictionary_blob=False,
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
            if param == "file_type":
                if value == "application/json":
                    value = "json"
                elif value == "application/json_v1":
                    value = "application/json_v1"
                elif value == "application/json_v2":
                    value = "application/json_v2"
                elif value == "text/csv":
                    value = "csv"
                else:
                    errors.append(
                        f"Invalid {param}: {value}. Must be application/json, application/json_v1, application/json_v2, or text/csv."
                    )
            elif param == "json_version":
                if value not in ["v1", "v2"]:
                    errors.append(f"Invalid {param}: {value}. Must be v1 or v2.")
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

    # Validate data_dictionary_blob
    if check_data_dictionary_blob:
        data_dictionary_blob = conf.get("data_dictionary_blob")
        if data_dictionary_blob == "None":
            validated_params["data_dictionary_blob"] = None
        else:
            validated_params["data_dictionary_blob"] = data_dictionary_blob

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
    string_params = ["scan_report_blob"]
    return _validate_dag_params(
        int_params=int_params,
        string_params=string_params,
        check_data_dictionary_blob=True,
        **context,
    )


def validate_params_rules_export(**context):
    """Validates parameters required for rules export DAG tasks."""
    int_params = ["scan_report_id", "user_id"]
    string_params = ["file_type", "scan_report_name", "json_version"]
    return _validate_dag_params(
        int_params=int_params,
        string_params=string_params,
        **context,
    )


def pull_validated_params(kwargs: dict, task_id: str) -> ValidatedParams:
    """Pull parameters from XCom for a given task"""
    task_instance: TaskInstance = kwargs["ti"]
    return task_instance.xcom_pull(task_ids=task_id)


def connect_to_storage() -> None:
    """
    Connects to the storage service based on the storage type.
    """
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
                    extra={"connection_string": AIRFLOW_VAR_WASB_CONNECTION_STRING},
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
                        "endpoint_url": AIRFLOW_VAR_MINIO_ENDPOINT,
                        "aws_access_key_id": AIRFLOW_VAR_MINIO_ACCESS_KEY,
                        "aws_secret_access_key": AIRFLOW_VAR_MINIO_SECRET_KEY,
                    },
                )
                session.add(conn)
                session.commit()
                logging.info("Created new MinIO connection")

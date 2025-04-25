import logging
import ast
import json
from airflow.providers.postgres.hooks.postgres import PostgresHook
from enum import Enum
from airflow.operators.python import PythonOperator


# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")
# Set up logger
logger = logging.getLogger(__name__)


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


# TODO: more error handling and comments for this function
def process_field_vocab_pairs(field_vocab_pairs: str):
    """Extract and validate parameters from DAG run configuration"""

    # Check if field_vocab_pairs is a string and try to parse it as JSON
    if isinstance(field_vocab_pairs, str):
        try:
            field_vocab_pairs = ast.literal_eval(field_vocab_pairs)
            print("Parsed field_vocab_pairs from string: ", field_vocab_pairs)
        except json.JSONDecodeError:
            print("Failed to parse field_vocab_pairs as JSON")

    return field_vocab_pairs


def update_job_status(
    scan_report: int,
    scan_report_table: int,
    stage: JobStageType,
    status: StageStatusType,
    details: str = "",
):
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
    return PythonOperator(
        task_id=task_id,
        python_callable=python_callable,
        provide_context=provide_context,
        dag=dag,
    )

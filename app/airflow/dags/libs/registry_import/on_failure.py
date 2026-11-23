"""
The DAG's failure callback: mark the ImportJob FAILED, say why, and remove any
mapping set the job had loaded but not finished.
"""

from __future__ import annotations

import logging
from contextlib import closing
from typing import Any

from airflow.exceptions import AirflowFailException

from libs.db import pg_hook
from libs.notifications import NotificationType, create_import_job_notification
from libs.registry_import import queries
from libs.registry_import.helpers import (
    CARROT_DIRECT_PUBLISH,
    IMPORT_JOB_URL,
    drop_temp_rules_table,
    temp_rules_table_suffix,
)

# ImportJob.error_message is shown to the submitter by the API.
INTERNAL_ERROR_MESSAGE = (
    "The import failed because of an internal error. Please try again, and "
    "contact an administrator if it keeps failing."
)


def failure_message(context: dict[str, Any]) -> str:
    """
    The reason to show the submitter. Tasks raise AirflowFailException with a
    message written for them; anything else may hold connection details or SQL,
    so it stays in the task log.
    """
    exception = context.get("exception")
    if isinstance(exception, AirflowFailException):
        return str(exception)
    if exception is not None:
        logging.error(f"registry_import failed: {exception!s}")
        return INTERNAL_ERROR_MESSAGE
    if context.get("reason"):
        return str(context["reason"])
    task_id = getattr(context.get("task_instance"), "task_id", "unknown")
    return f"Task '{task_id}' was timed out or failed unexpectedly"


def update_import_job_on_failure(context) -> None:
    """
    Mark the ImportJob FAILED, record why, and notify its submitter. Used as
    both the tasks' and the DAG's on_failure_callback: the task callback has the
    exception; the DAG callback also catches timeouts. Only the first records.

    The load commits before finalize runs, so a job can fail with its set still
    in the tables. That set was never finished: it is deleted, in the same
    transaction, so it doesn't hold the set_version or decide the set_uri's owner
    and the import can be submitted again. finalize marks a job SUCCEEDED in the
    transaction that sets the final status, so a finished set is never removed.
    """
    try:
        conf = context["dag_run"].conf or {}
        import_job_id = conf.get("import_job_id")
        if not import_job_id:
            logging.error("registry_import failed without an import_job_id in its conf")
            return
        message = failure_message(context)

        with closing(pg_hook.get_conn()) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    queries.mark_import_job_failed_query,
                    {"import_job_id": import_job_id, "error_message": message},
                )
                updated = cursor.fetchone()
                if updated:
                    params = {"import_job_id": import_job_id}
                    cursor.execute(queries.delete_job_mappings_query, params)
                    cursor.execute(queries.delete_job_mapping_sets_query, params)
            conn.commit()

        if updated:
            create_import_job_notification(
                import_job_id,
                NotificationType.REGISTRY_IMPORT_FAILED,
                "Your mapping set import failed",
                IMPORT_JOB_URL.format(import_job_id=import_job_id),
            )

        # A failed direct publish may leave its temp rules table behind.
        scan_report_id = conf.get("scan_report_id")
        if conf.get("origin") == CARROT_DIRECT_PUBLISH and scan_report_id:
            try:
                suffix = temp_rules_table_suffix(import_job_id)
                scan_report_id = int(scan_report_id)
            except (TypeError, ValueError):
                # validate_params rejected these ids, so no table was created
                logging.info("Invalid ids in the run conf: no temp rules table to drop")
            else:
                drop_temp_rules_table(scan_report_id, suffix)
    except Exception as e:
        logging.error(f"Failed to update ImportJob on failure: {e!s}")

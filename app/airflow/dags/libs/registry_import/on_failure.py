"""The DAG's failure callback: mark the ImportJob FAILED and say why."""

from __future__ import annotations

import logging
from contextlib import closing

from libs.db import pg_hook
from libs.notifications import NotificationType, create_import_job_notification
from libs.registry_import import queries
from libs.registry_import.helpers import (
    CARROT_DIRECT_PUBLISH,
    IMPORT_JOB_URL,
    drop_temp_rules_table,
    temp_rules_table_suffix,
)


def update_import_job_on_failure(context) -> None:
    """
    Mark the ImportJob FAILED, record why, and notify its submitter. Used as
    both the tasks' and the DAG's on_failure_callback: the task callback has the
    exception; the DAG callback also catches timeouts. Only the first records.
    """
    try:
        conf = context["dag_run"].conf or {}
        import_job_id = conf.get("import_job_id")
        if not import_job_id:
            logging.error("registry_import failed without an import_job_id in its conf")
            return
        exception = context.get("exception")
        task_instance = context.get("task_instance")
        if exception is not None:
            message = str(exception)
        elif context.get("reason"):
            message = str(context["reason"])
        else:
            task_id = getattr(task_instance, "task_id", "unknown")
            message = f"Task '{task_id}' was timed out or failed unexpectedly"

        with closing(pg_hook.get_conn()) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    queries.mark_import_job_failed_query,
                    {"import_job_id": import_job_id, "error_message": message},
                )
                updated = cursor.fetchone()
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

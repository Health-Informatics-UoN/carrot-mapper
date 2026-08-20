import logging
from enum import StrEnum

from airflow.providers.postgres.hooks.postgres import PostgresHook

from libs.settings import AIRFLOW_DAGRUN_TIMEOUT

# PostgreSQL connection hook
pg_hook = PostgresHook(
    postgres_conn_id="postgres_db_conn",
    options=f"-c statement_timeout={float(AIRFLOW_DAGRUN_TIMEOUT) * 60 * 1000}ms",
)


class NotificationType(StrEnum):
    """
    Mirrors app/api/notifications/models.py::NotificationType. Airflow and
    the Django API are separate codebases with no shared import, so these
    values are kept in sync by hand - the Django side is the source of
    truth.
    """

    SCAN_REPORT_PROCESSING_COMPLETE = "scanreport.processing_complete"
    SCAN_REPORT_PROCESSING_FAILED = "scanreport.processing_failed"
    AUTOMAP_COMPLETE = "automap.complete"
    AUTOMAP_FAILED = "automap.failed"
    RULES_EXPORT_COMPLETE = "rules.export_complete"
    RULES_EXPORT_FAILED = "rules.export_failed"


def create_notification(
    scan_report_id: int, notif_type: str, text: str, url: str = ""
) -> None:
    """
    Insert a Notification row for the author of the given scan report.

    Mirrors update_job_status()'s pattern of writing directly to Postgres via
    pg_hook, since Airflow has no HTTP channel back into the Django API. The
    recipient is resolved via mapping_scanreport.author_id in the same
    query, so callers only ever need the scan_report_id every DAG already
    carries - no DAG conf needs to start threading a user_id through just
    for this.

    Failures here are logged, not raised: a missing notification should
    never fail (or retry) an otherwise-successful DAG run.
    """
    insert_query = """
        INSERT INTO notifications_notification (
            recipient_id, notif_type, text, url, created_at, updated_at
        )
        SELECT author_id, %(notif_type)s, %(text)s, %(url)s, NOW(), NOW()
        FROM mapping_scanreport
        WHERE id = %(scan_report_id)s AND author_id IS NOT NULL
    """
    try:
        pg_hook.run(
            insert_query,
            parameters={
                "scan_report_id": scan_report_id,
                "notif_type": notif_type,
                "text": text,
                "url": url,
            },
        )
    except Exception as e:
        logging.error(
            f"Failed to create notification for scan_report={scan_report_id}, "
            f"notif_type={notif_type}: {e}"
        )

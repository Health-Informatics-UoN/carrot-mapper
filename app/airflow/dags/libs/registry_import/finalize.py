"""Step 5: publish the set (unless a DRAFT was asked for), mark the job SUCCEEDED."""

from __future__ import annotations

from contextlib import closing

from airflow.exceptions import AirflowFailException

from libs.db import pg_hook
from libs.notifications import NotificationType, create_import_job_notification
from libs.registry_import import queries
from libs.registry_import.full_validate_and_load_checks import (
    PUBLISHED,
    IssueLog,
    normalise_overrides,
)
from libs.registry_import.helpers import MAPPING_SET_URL
from libs.utils import pull_validated_params


def finalize(**kwargs) -> None:
    params = pull_validated_params(kwargs, "validate_params_registry_import")
    import_job_id = params["import_job_id"]
    _, status = normalise_overrides(params["overrides"], IssueLog(0))
    with closing(pg_hook.get_conn()) as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    queries.publish_mapping_set_query,
                    {"status": status, "import_job_id": import_job_id},
                )
                row = cursor.fetchone()
                if not row:
                    raise AirflowFailException(
                        f"No mapping set was loaded for ImportJob {import_job_id}"
                    )
                cursor.execute(
                    queries.mark_import_job_succeeded_query,
                    {"import_job_id": import_job_id},
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    mapping_set_id, title = row
    done = "published to" if status == PUBLISHED else "saved as a draft in"
    create_import_job_notification(
        import_job_id,
        NotificationType.REGISTRY_IMPORT_COMPLETE,
        f"'{title}' was {done} the mappings registry",
        MAPPING_SET_URL.format(mapping_set_id=mapping_set_id),
    )

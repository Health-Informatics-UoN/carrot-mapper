"""
Write a validated ImportPlan to the registry tables in ONE transaction, so a
failed run never leaves a half-imported set behind:

1. delete any MappingSet this job created before (makes retries idempotent);
2. insert the MappingSet (status DRAFT; finalize publishes it);
3. COPY the rows into a temp staging table;
4. insert the new subject and object Terms (existing ones are reused);
5. insert the Mappings, joining staging rows to their Terms;
6. record the job's stats.

Takes a DB-API connection rather than the Airflow hook, so tests can run it
against any database with the registry schema.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from libs.registry_import import queries
from libs.registry_import.validate import STAGING_COLUMNS, ImportPlan


class LoadError(Exception):
    """The load can't go ahead (not a transient database problem)."""


def load_plan(
    conn,
    plan: ImportPlan,
    *,
    import_job_id: str,
    origin: str,
    file_key: str,
    scan_report_id: int | None = None,
) -> dict[str, Any]:
    """
    Load ``plan`` and commit. Returns the stats also stored on the ImportJob.
    Rolls back and re-raises on any error.
    """
    if not plan.ok:
        raise LoadError(f"Refusing to load an invalid file: {plan.summary()}")
    if not plan.rows:
        raise LoadError("Refusing to load a file with no mappings")

    record = plan.mapping_set
    mapping_set_id = str(uuid.uuid4())
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                queries.delete_job_mappings_query, {"import_job_id": import_job_id}
            )
            cursor.execute(
                queries.delete_job_mapping_sets_query, {"import_job_id": import_job_id}
            )

            cursor.execute(
                queries.get_conflicting_set_query,
                {
                    "set_uri": record.set_uri,
                    "set_version": record.set_version,
                    "import_job_id": import_job_id,
                },
            )
            if cursor.fetchone():
                raise LoadError(
                    f"Mapping set {record.set_uri} version {record.set_version} "
                    "already exists; publish corrections as a new mapping_set_version"
                )

            cursor.execute(
                queries.insert_mapping_set_query,
                {
                    "id": mapping_set_id,
                    "set_uri": record.set_uri,
                    "set_version": record.set_version,
                    "title": record.title,
                    "description": record.description,
                    "license_id": record.license_id,
                    "origin_id": origin,
                    "import_job_id": import_job_id,
                    "source_scan_report_id": scan_report_id,
                    "sssom_version": record.sssom_version,
                    "creator_ids": json.dumps(record.creator_ids),
                    "publication_date": record.publication_date,
                    "subject_source": record.subject_source,
                    "subject_source_version": record.subject_source_version,
                    "object_source": record.object_source,
                    "object_source_version": record.object_source_version,
                    "curie_map": json.dumps(record.curie_map),
                    "extra_metadata": json.dumps(
                        record.extra_metadata, ensure_ascii=False
                    ),
                    "file_key": file_key,
                },
            )

            cursor.execute(queries.create_staging_table_query)
            with cursor.copy(
                queries.copy_staging_query.format(columns=", ".join(STAGING_COLUMNS))
            ) as copy:
                for row in plan.rows:
                    copy.write_row(row)

            cursor.execute(queries.insert_subject_terms_query)
            subject_terms_created = cursor.rowcount
            cursor.execute(queries.insert_object_terms_query)
            object_terms_created = cursor.rowcount

            cursor.execute(
                queries.insert_mappings_query, {"mapping_set_id": mapping_set_id}
            )
            mappings_created = cursor.rowcount
            if mappings_created != len(plan.rows):
                raise LoadError(
                    f"Inserted {mappings_created} mappings for {len(plan.rows)} rows"
                )

            stats = {
                "rows": len(plan.rows),
                "mappings_created": mappings_created,
                "terms_created": subject_terms_created + object_terms_created,
                "subject_terms_created": subject_terms_created,
                "object_terms_created": object_terms_created,
                "warnings": plan.issues.warnings,
                "mapping_set_id": mapping_set_id,
            }
            cursor.execute(
                queries.set_import_job_stats_query,
                {"stats": json.dumps(stats), "import_job_id": import_job_id},
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    logging.info(f"Loaded import job {import_job_id}: {stats}")
    return stats

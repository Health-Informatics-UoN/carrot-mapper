"""
full_validate_and_load helper: write a validated file to the registry tables in
ONE transaction, so a failed run never leaves a half-imported set behind:

1. lock the set_uri, so concurrent imports of it take turns;
2. delete any MappingSet this job created before (makes retries idempotent);
3. check the version is new and the set_uri is this import's to add to;
4. insert the MappingSet (status DRAFT; finalize publishes it);
5. register the prefixes the terms use, checking none changed since validation;
6. COPY the rows into a temp staging table;
7. insert the new subject and object Terms (existing ones are reused);
8. insert the Mappings, joining staging rows to their Terms;
9. record the job's stats.

Steps 3 and 5 repeat checks made during validation: another import may have
committed in between.

load_plan takes a DB-API connection rather than the Airflow hook, so tests can
run it against any database with the registry schema.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from libs.registry_import import queries
from libs.registry_import.full_validate_and_load_checks import (
    STAGING_COLUMNS,
    ImportPlan,
    SetOwner,
    set_owner_error,
)


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
    Rolls back and re-raises on any error. The set's publisher is the job's
    submitted_by.
    """
    if not plan.ok:
        raise LoadError(f"Refusing to load an invalid file: {plan.summary()}")
    if not plan.rows:
        raise LoadError("Refusing to load a file with no mappings")

    record = plan.mapping_set
    mapping_set_id = str(uuid.uuid4())
    try:
        with conn.cursor() as cursor:
            cursor.execute(queries.lock_set_uri_query, {"set_uri": record.set_uri})
            cursor.execute(
                queries.get_import_job_submitter_query,
                {"import_job_id": import_job_id},
            )
            submitter = cursor.fetchone()
            if submitter is None:
                raise LoadError(f"ImportJob {import_job_id} does not exist")
            publisher_id = submitter[0]
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
                queries.get_set_first_version_query,
                {"set_uri": record.set_uri, "import_job_id": import_job_id},
            )
            first = cursor.fetchone()
            owner_error = set_owner_error(
                SetOwner(*first) if first else None,
                origin=origin,
                scan_report_id=scan_report_id,
                user_id=publisher_id,
            )
            if owner_error:
                raise LoadError(
                    f"Mapping set {record.set_uri} already exists and {owner_error}"
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
                    "publisher_id": publisher_id,
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

            _register_prefixes(cursor, plan.prefixes)

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


def _register_prefixes(cursor, prefixes: dict[str, str]) -> None:
    """
    Add the terms' prefixes to registry_prefix and check each is bound as the
    file was validated against. It isn't if another import registered the name
    or the namespace in the meantime; a retry validates against the new state.
    """
    names = sorted(prefixes)
    cursor.execute(
        queries.insert_prefixes_query,
        {"prefixes": names, "namespaces": [prefixes[n] for n in names]},
    )
    cursor.execute(queries.get_prefixes_by_name_query, {"prefixes": names})
    stored = dict(cursor.fetchall())
    changed = [n for n in names if stored.get(n) != prefixes[n]]
    if changed:
        raise LoadError(
            f"Prefixes {changed} were registered for other namespaces while this "
            "file was being imported; submit it again"
        )

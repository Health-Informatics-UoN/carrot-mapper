"""
The registry_import load and task flow against a real Postgres database with
the API's migrations applied (registry, mapping, notifications, auth...).

Skipped unless REGISTRY_IMPORT_TEST_DATABASE_URL is set, e.g.

    REGISTRY_IMPORT_TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/carrot

Each test creates its own rows (with unique ids and CURIE prefixes) and
deletes them afterwards; nothing else in the database is touched.
"""

from __future__ import annotations

import os
import uuid
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest
from airflow.exceptions import AirflowFailException
from libs.registry_import import (
    finalize,
    full_validate_and_load,
    helpers,
    on_failure,
    prepare_source,
    queries,
    validate_params,
)
from libs.registry_import.full_validate_and_load_checks import Vocabulary, build_import
from libs.registry_import.full_validate_and_load_db import LoadError, load_plan
from libs.registry_import.full_validate_and_load_parse import parse_sssom

DATABASE_URL = os.getenv("REGISTRY_IMPORT_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="REGISTRY_IMPORT_TEST_DATABASE_URL is not set"
)

if DATABASE_URL:
    # libs.db's pg_hook reads its connection from this variable when it connects.
    os.environ.setdefault(
        "AIRFLOW_CONN_POSTGRES_DB_CONN",
        DATABASE_URL.replace("postgresql://", "postgres://", 1),
    )

# What SSSOM files usually cite, and what the registry stores (license_sync).
CC_BY = "https://creativecommons.org/licenses/by/4.0/"
SPDX_CC_BY = "https://spdx.org/licenses/CC-BY-4.0"


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    with closing(psycopg.connect(DATABASE_URL)) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('registry_importjob')")
            if cursor.fetchone()[0] is None:
                pytest.skip("Database has no registry tables: run the API migrations")
        connection.commit()
        yield connection


def _dummy(data_type: str):
    if "timestamp" in data_type:
        return datetime.now(UTC)
    if data_type == "date":
        return date(1970, 1, 1)
    if data_type == "boolean":
        return False
    if data_type in ("integer", "bigint", "smallint"):
        return 0
    return "x"


def insert(cursor, table_name: str, /, returning: str | None = "id", **values):
    """
    Insert a row, filling other required columns with dummy values. Returns
    the ``returning`` column. ``table_name`` may be schema-qualified.
    """
    schema, _, table = table_name.rpartition(".")
    cursor.execute(
        """
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s AND is_nullable = 'NO'
            AND column_default IS NULL AND is_identity = 'NO'
        """,
        (schema or "public", table),
    )
    for column, data_type in cursor.fetchall():
        values.setdefault(column, _dummy(data_type))
    columns = ", ".join(f'"{c}"' for c in values)
    placeholders = ", ".join(["%s"] * len(values))
    sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    cursor.execute(
        sql + (f" RETURNING {returning}" if returning else ""), list(values.values())
    )
    return cursor.fetchone()[0] if returning else None


class Cleanup:
    """Rows a test created, deleted in a safe order afterwards."""

    def __init__(self, connection):
        self.conn = connection
        self.jobs: list[str] = []
        self.prefixes: list[str] = []
        self.terms: set[str] = set()
        self.rows: list[tuple[str, int]] = []
        self.users: list[int] = []
        # (table, key column, key) of OMOP rows a test added; deleted last
        self.omop: list[tuple[str, str, Any]] = []

    def run(self):
        self.conn.rollback()
        with self.conn.cursor() as cursor:
            for job in self.jobs:
                cursor.execute(
                    queries.delete_job_mappings_query, {"import_job_id": job}
                )
                cursor.execute(
                    queries.delete_job_mapping_sets_query, {"import_job_id": job}
                )
                cursor.execute("DELETE FROM registry_importjob WHERE id = %s", (job,))
            cursor.execute(
                "DELETE FROM registry_term WHERE canonical_iri = ANY(%s)",
                (list(self.terms),),
            )
            for prefix in self.prefixes:
                cursor.execute(
                    "DELETE FROM registry_term WHERE canonical_iri LIKE %s",
                    (f"{prefix}:%",),
                )
            for table, row_id in reversed(self.rows):
                cursor.execute(f"DELETE FROM {table} WHERE id = %s", (row_id,))
            for user in self.users:
                cursor.execute(
                    "DELETE FROM notifications_notification WHERE recipient_id = %s",
                    (user,),
                )
                cursor.execute("DELETE FROM users_profile WHERE user_id = %s", (user,))
                cursor.execute("DELETE FROM auth_user WHERE id = %s", (user,))
            for table, column, key in reversed(self.omop):
                cursor.execute(f"DELETE FROM {table} WHERE {column} = %s", (key,))
        self.conn.commit()


@pytest.fixture
def cleanup(conn):
    c = Cleanup(conn)
    yield c
    c.run()


@pytest.fixture(autouse=True)
def cc_by_license(conn):
    """
    CC-BY-4.0 as the license_sync DAG stores it. Inserted only when missing
    (a synced database already has it), and then removed afterwards.
    """
    if not DATABASE_URL:
        yield
        return
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO registry_license
                (id, license_iri, spdx_id, label, is_open, is_deprecated, see_also)
            VALUES ('CC-BY-4.0', %s, 'CC-BY-4.0',
                'Creative Commons Attribution 4.0 International', true, false,
                '["https://creativecommons.org/licenses/by/4.0/legalcode"]')
            ON CONFLICT (id) DO NOTHING
            RETURNING id
            """,
            (SPDX_CC_BY,),
        )
        inserted = cursor.fetchone() is not None
    conn.commit()
    yield
    if inserted:
        conn.rollback()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM registry_license WHERE id = 'CC-BY-4.0'")
        conn.commit()


@pytest.fixture
def user(conn, cleanup):
    with conn.cursor() as cursor:
        user_id = insert(
            cursor, "auth_user", username=f"jane_doe_{uuid.uuid4().hex[:6]}"
        )
    conn.commit()
    cleanup.users.append(user_id)
    return user_id


def make_job(conn, cleanup, user_id, origin="SSSOM_UPLOAD", file_key="") -> str:
    job_id = str(uuid.uuid4())
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO registry_importjob (id, submitted_by_id, status, origin_id,
                file_key, validation_issues, dag_run_id, error_message, params, stats)
            VALUES (%s, %s, 'PENDING', %s, %s, '[]', '', '', '{}', '{}')
            """,
            (job_id, user_id, origin, file_key),
        )
    conn.commit()
    cleanup.jobs.append(job_id)
    return job_id


def unique_prefixes(cleanup) -> tuple[str, str]:
    tag = uuid.uuid4().hex[:8].upper()
    subject, obj = f"S{tag}", f"O{tag}"
    cleanup.prefixes += [subject, obj]
    return subject, obj


def sssom(
    subject: str, obj: str, version: str = "1.0", rows: int = 3, set_uri=None
) -> str:
    set_uri = set_uri or f"https://example.org/sets/{subject.lower()}"
    lines = [
        "#curie_map:",
        f"#  {subject}: http://example.org/{subject}/",
        f"#  {obj}: http://example.org/{obj}/",
        f"#mapping_set_id: {set_uri}",
        f'#mapping_set_version: "{version}"',
        "#mapping_set_title: Test set",
        f"#license: {CC_BY}",
        "#mapping_date: 2026-11-01",
        "subject_id\tsubject_label\tpredicate_id\tobject_id\tobject_label\tmapping_justification\tconfidence\tcomment",
    ]
    for i in range(rows):
        lines.append(
            f"{subject}:{i}\tsubject {i}\tskos:exactMatch\t{obj}:{i % 2}\tobject {i % 2}"
            f"\tsemapv:ManualMappingCuration\t0.{i + 1}\tnote {i}"
        )
    return "\n".join(lines) + "\n"


def plan_for(conn, text: str):
    """build_import with the database's vocabularies, licensed CC-BY-4.0."""
    with conn.cursor() as cursor:
        cursor.execute(queries.get_predicates_query)
        predicates = {r[0] for r in cursor.fetchall()}
        cursor.execute(queries.get_justifications_query)
        justifications = {r[0] for r in cursor.fetchall()}
    conn.rollback()
    return build_import(
        parse_sssom(text),
        Vocabulary(predicates, justifications),
        license_id="CC-BY-4.0",
    )


def fetch(conn, query, *params):
    with conn.cursor() as cursor:
        cursor.execute(query, params)
        result = cursor.fetchall()
    conn.rollback()
    return result


# ---------------------------------------------------------------------------
# load_plan
# ---------------------------------------------------------------------------


def test_load_inserts_set_terms_and_mappings(conn, cleanup, user):
    subject, obj = unique_prefixes(cleanup)
    job = make_job(conn, cleanup, user)
    plan = plan_for(conn, sssom(subject, obj))
    assert plan.ok, plan.issues.as_dicts()

    stats = load_plan(
        conn, plan, import_job_id=job, origin="SSSOM_UPLOAD", file_key="k"
    )

    assert stats["rows"] == 3 and stats["mappings_created"] == 3
    assert (stats["subject_terms_created"], stats["object_terms_created"]) == (3, 2)
    [(set_id, status, title, license_id, file_key, curie_map, extra)] = fetch(
        conn,
        "SELECT id::text, status_id, title, license_id, file_key, curie_map, extra_metadata "
        "FROM registry_mappingset WHERE import_job_id = %s",
        job,
    )
    assert (status, title, license_id, file_key) == (
        "DRAFT",
        "Test set",
        "CC-BY-4.0",
        "k",
    )
    assert subject in curie_map
    assert extra == {"mapping_date": "2026-11-01"}
    mappings = fetch(
        conn,
        "SELECT s.canonical_iri, o.canonical_iri, m.confidence, m.mapping_date::text, m.comment "
        "FROM registry_mapping m JOIN registry_term s ON s.id = m.subject_id "
        "JOIN registry_term o ON o.id = m.object_id WHERE m.mapping_set_id = %s ORDER BY m.id",
        set_id,
    )
    assert mappings[0] == (f"{subject}:0", f"{obj}:0", 0.1, "2026-11-01", "note 0")
    [(job_stats,)] = fetch(
        conn, "SELECT stats FROM registry_importjob WHERE id = %s", job
    )
    assert job_stats == stats


def test_reloading_the_same_job_is_idempotent(conn, cleanup, user):
    subject, obj = unique_prefixes(cleanup)
    job = make_job(conn, cleanup, user)
    plan = plan_for(conn, sssom(subject, obj))
    load_plan(conn, plan, import_job_id=job, origin="SSSOM_UPLOAD", file_key="k")
    again = load_plan(
        conn, plan, import_job_id=job, origin="SSSOM_UPLOAD", file_key="k"
    )

    assert again["terms_created"] == 0
    assert fetch(
        conn, "SELECT count(*) FROM registry_mappingset WHERE import_job_id = %s", job
    ) == [(1,)]
    assert fetch(
        conn,
        "SELECT count(*) FROM registry_mapping m JOIN registry_mappingset s "
        "ON s.id = m.mapping_set_id WHERE s.import_job_id = %s",
        job,
    ) == [(3,)]


def test_new_version_reuses_terms(conn, cleanup, user):
    subject, obj = unique_prefixes(cleanup)
    first, second = make_job(conn, cleanup, user), make_job(conn, cleanup, user)
    load_plan(
        conn,
        plan_for(conn, sssom(subject, obj, "1.0")),
        import_job_id=first,
        origin="SSSOM_UPLOAD",
        file_key="a",
    )
    stats = load_plan(
        conn,
        plan_for(conn, sssom(subject, obj, "2.0")),
        import_job_id=second,
        origin="SSSOM_UPLOAD",
        file_key="b",
    )
    assert stats["terms_created"] == 0 and stats["mappings_created"] == 3


def test_existing_set_version_is_refused(conn, cleanup, user):
    subject, obj = unique_prefixes(cleanup)
    plan = plan_for(conn, sssom(subject, obj))
    first, second = make_job(conn, cleanup, user), make_job(conn, cleanup, user)
    load_plan(conn, plan, import_job_id=first, origin="SSSOM_UPLOAD", file_key="a")
    with pytest.raises(LoadError, match="already exists"):
        load_plan(conn, plan, import_job_id=second, origin="SSSOM_UPLOAD", file_key="b")
    assert fetch(
        conn,
        "SELECT count(*) FROM registry_mappingset WHERE import_job_id = %s",
        second,
    ) == [(0,)]


def test_failure_mid_load_leaves_nothing_behind(conn, cleanup, user, monkeypatch):
    subject, obj = unique_prefixes(cleanup)
    job = make_job(conn, cleanup, user)
    plan = plan_for(conn, sssom(subject, obj))
    # The set and terms are inserted, then the mappings insert fails
    monkeypatch.setattr(queries, "insert_mappings_query", "SELECT 1 / 0")

    with pytest.raises(psycopg.errors.DivisionByZero):
        load_plan(conn, plan, import_job_id=job, origin="SSSOM_UPLOAD", file_key="k")

    assert fetch(
        conn, "SELECT count(*) FROM registry_mappingset WHERE import_job_id = %s", job
    ) == [(0,)]
    assert fetch(
        conn,
        "SELECT count(*) FROM registry_term WHERE canonical_iri LIKE %s",
        f"{subject}:%",
    ) == [(0,)]
    assert fetch(conn, "SELECT stats FROM registry_importjob WHERE id = %s", job) == [
        ({},)
    ]


def test_invalid_plan_is_never_loaded(conn, cleanup, user):
    subject, obj = unique_prefixes(cleanup)
    job = make_job(conn, cleanup, user)
    bad = sssom(subject, obj).replace("skos:exactMatch", "skos:madeUp")
    with pytest.raises(LoadError, match="invalid"):
        load_plan(
            conn,
            plan_for(conn, bad),
            import_job_id=job,
            origin="SSSOM_UPLOAD",
            file_key="k",
        )


# ---------------------------------------------------------------------------
# The DAG's tasks, run in order with fake storage
# ---------------------------------------------------------------------------


class FakeStorage:
    def __init__(self, tmp_path: Path):
        self.blobs: dict[tuple[str, str], bytes] = {}
        self.tmp = tmp_path

    def upload(self, container_name, blob_name, data, content_type):
        self.blobs[(container_name, blob_name)] = data.getvalue()

    def download(self, container_name, blob_name) -> Path:
        path = self.tmp / blob_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.blobs[(container_name, blob_name)])
        return path


@pytest.fixture
def storage(tmp_path, monkeypatch):
    fake = FakeStorage(tmp_path)
    monkeypatch.setattr(prepare_source, "upload_blob_to_storage", fake.upload)
    monkeypatch.setattr(full_validate_and_load, "download_blob_to_tmp", fake.download)
    return fake


def run_dag(conf: dict) -> None:
    """Run the DAG's tasks in order, as Airflow would, raising the first failure."""
    dag_run = SimpleNamespace(conf=conf, run_id=f"manual__{uuid.uuid4().hex[:8]}")
    context = {"dag_run": dag_run}
    params = validate_params.validate_params_registry_import(**context)

    def xcom_pull(task_ids):
        # every step must read the first task's output, by its exact id
        assert task_ids == "validate_params_registry_import", task_ids
        return params

    ti = SimpleNamespace(xcom_pull=xcom_pull)
    steps = (
        prepare_source.prepare_source,
        full_validate_and_load.full_validate_and_load,
        finalize.finalize,
    )
    for task in steps:
        try:
            task(ti=ti, dag_run=dag_run)
        except Exception as e:
            # what Airflow does on the final failure: task callback, then DAG callback
            on_failure.update_import_job_on_failure(
                {"dag_run": dag_run, "exception": e}
            )
            on_failure.update_import_job_on_failure(
                {"dag_run": dag_run, "reason": "task_failure"}
            )
            raise


def job_row(conn, job):
    [row] = fetch(
        conn,
        "SELECT status, error_message, validation_issues, stats, file_key, dag_run_id "
        "FROM registry_importjob WHERE id = %s",
        job,
    )
    return dict(
        zip(("status", "error", "issues", "stats", "file_key", "dag_run_id"), row)
    )


def notifications(conn, user):
    return fetch(
        conn,
        "SELECT notif_type, text, url FROM notifications_notification "
        "WHERE recipient_id = %s ORDER BY id",
        user,
    )


def test_dag_imports_an_upload(conn, cleanup, user, storage):
    subject, obj = unique_prefixes(cleanup)
    job = make_job(conn, cleanup, user)
    key = helpers.file_key_for(job)
    storage.blobs[("registry-sssom", key)] = sssom(subject, obj).encode()

    run_dag(
        {
            "import_job_id": job,
            "origin": "SSSOM_UPLOAD",
            "user_id": user,
            "file_key": key,
            # the License id the upload endpoint has checked
            "overrides": {"license": "CC-BY-4.0"},
        }
    )

    row = job_row(conn, job)
    assert row["status"] == "SUCCEEDED" and row["error"] == ""
    assert fetch(
        conn,
        "SELECT license_id FROM registry_mappingset WHERE import_job_id = %s",
        job,
    ) == [("CC-BY-4.0",)]
    assert row["file_key"] == key and row["dag_run_id"].startswith("manual__")
    assert row["stats"]["mappings_created"] == 3
    [(set_id, status, published)] = fetch(
        conn,
        "SELECT id::text, status_id, published_at IS NOT NULL FROM registry_mappingset "
        "WHERE import_job_id = %s",
        job,
    )
    assert (status, published) == ("PUBLISHED", True)
    assert notifications(conn, user) == [
        (
            "registry.import_complete",
            "'Test set' was published to the mappings registry",
            f"/registry/mapping-sets/{set_id}",
        )
    ]


def test_dag_records_validation_failure_once(conn, cleanup, user, storage):
    subject, obj = unique_prefixes(cleanup)
    job = make_job(conn, cleanup, user)
    key = helpers.file_key_for(job)
    bad = sssom(subject, obj).replace("skos:exactMatch", "skos:madeUp")
    storage.blobs[("registry-sssom", key)] = bad.encode()

    with pytest.raises(AirflowFailException, match="failed validation"):
        run_dag(
            {
                "import_job_id": job,
                "origin": "SSSOM_UPLOAD",
                "user_id": user,
                "file_key": key,
                "overrides": {"license": "CC-BY-4.0"},
            }
        )

    row = job_row(conn, job)
    assert row["status"] == "FAILED"
    assert "unknown_predicate" in row["error"]
    errors = [i for i in row["issues"] if i["level"] == "error"]
    assert {i["code"] for i in errors} == {"unknown_predicate"}
    assert [i["line"] for i in errors] == [10, 11, 12]
    assert fetch(
        conn, "SELECT count(*) FROM registry_mappingset WHERE import_job_id = %s", job
    ) == [(0,)]
    assert [n[0] for n in notifications(conn, user)] == ["registry.import_failed"]


def test_dag_refuses_a_job_that_already_succeeded(conn, cleanup, user, storage):
    subject, obj = unique_prefixes(cleanup)
    job = make_job(conn, cleanup, user)
    key = helpers.file_key_for(job)
    storage.blobs[("registry-sssom", key)] = sssom(subject, obj).encode()
    conf = {
        "import_job_id": job,
        "origin": "SSSOM_UPLOAD",
        "user_id": user,
        "file_key": key,
    }
    run_dag(conf)
    with pytest.raises(AirflowFailException, match="already succeeded"):
        run_dag(conf)


def test_dag_refuses_an_existing_set_version(conn, cleanup, user, storage):
    subject, obj = unique_prefixes(cleanup)
    jobs = [make_job(conn, cleanup, user), make_job(conn, cleanup, user)]
    for job in jobs:
        storage.blobs[("registry-sssom", helpers.file_key_for(job))] = sssom(
            subject, obj
        ).encode()

    def conf(job):
        return {
            "import_job_id": job,
            "origin": "SSSOM_UPLOAD",
            "user_id": user,
            "file_key": helpers.file_key_for(job),
            "overrides": {"license": "CC-BY-4.0"},
        }

    run_dag(conf(jobs[0]))
    with pytest.raises(AirflowFailException, match="set_version_exists"):
        run_dag(conf(jobs[1]))

    row = job_row(conn, jobs[1])
    assert row["status"] == "FAILED"
    assert "set_version_exists" in {i["code"] for i in row["issues"]}
    assert fetch(
        conn,
        "SELECT count(*) FROM registry_mappingset WHERE import_job_id = %s",
        jobs[1],
    ) == [(0,)]


@pytest.mark.parametrize(
    "conf, message",
    [
        ({"origin": "SSSOM_UPLOAD"}, "Missing required parameter: import_job_id"),
        ({"import_job_id": "nope", "origin": "SSSOM_UPLOAD"}, "Invalid import_job_id"),
        ({"import_job_id": str(uuid.uuid4()), "origin": "FAX"}, "Invalid origin"),
        (
            {
                "import_job_id": str(uuid.uuid4()),
                "origin": "CARROT_DIRECT_PUBLISH",
                "scan_report_id": 1,
                "overrides": {"set_uri": "https://x.org/s"},
            },
            "needs overrides.set_version; CARROT_DIRECT_PUBLISH needs overrides.title; "
            "CARROT_DIRECT_PUBLISH needs overrides.license; CARROT_DIRECT_PUBLISH "
            "needs overrides.include_author_orcid_ids",
        ),
        (
            {
                "import_job_id": str(uuid.uuid4()),
                "origin": "CARROT_DIRECT_PUBLISH",
                "scan_report_id": 1,
                "overrides": {
                    "set_uri": "https://x.org/s",
                    "set_version": "1",
                    "title": "T",
                    "license": "NOT-A-LICENSE",
                    "include_author_orcid_ids": "yes",
                },
            },
            "needs overrides.include_author_orcid_ids \\(true or false\\); "
            "Unknown license id: NOT-A-LICENSE",
        ),
        (
            {"import_job_id": str(uuid.uuid4()), "origin": "SSSOM_UPLOAD"},
            "does not exist",
        ),
    ],
)
def test_bad_parameters_fail_without_retrying(conn, conf, message):
    context = {"dag_run": SimpleNamespace(conf={"user_id": 1, **conf}, run_id="r")}
    with pytest.raises(AirflowFailException, match=message):
        validate_params.validate_params_registry_import(**context)


PUBLISHER_ORCID = "0000-0002-1825-009X"
AUTHOR_ORCID = "0000-0001-5109-3700"

# Used only when the database has no OMOP concepts of its own.
TEST_CONCEPTS = (
    (2_000_000_001, "Carrot test value concept", "Gender"),
    (2_000_000_002, "Carrot test field concept", "Observation"),
)
TEST_VOCABULARY = "CarrotTest"


def omop_concepts(conn, cleanup) -> list[SimpleNamespace]:
    """
    Two OMOP concepts to map to, with their domain and vocabulary version.

    Uses concepts already in the database when there are any (omop-lite's
    synthetic or real vocabularies), so the CDM's NOT NULL columns and any
    foreign keys are already satisfied. Only on a database with no concepts are
    test rows inserted. The first concept's vocabulary gets a row (with a
    version) if it has none. Anything inserted is deleted afterwards.
    """
    concepts = fetch(
        conn,
        "SELECT concept_id, domain_id, vocabulary_id FROM omop.concept "
        "ORDER BY concept_id LIMIT 2",
    )
    try:
        with conn.cursor() as cursor:
            if len(concepts) < 2:
                concepts = []
                for concept_id, name, domain in TEST_CONCEPTS:
                    insert(
                        cursor,
                        "omop.concept",
                        returning=None,
                        concept_id=concept_id,
                        concept_name=name,
                        domain_id=domain,
                        vocabulary_id=TEST_VOCABULARY,
                        concept_code=str(concept_id),
                    )
                    cleanup.omop.append(("omop.concept", "concept_id", concept_id))
                    concepts.append((concept_id, domain, TEST_VOCABULARY))
            vocabulary_id = concepts[0][2]
            cursor.execute(
                "SELECT vocabulary_version FROM omop.vocabulary WHERE vocabulary_id = %s",
                (vocabulary_id,),
            )
            existing = cursor.fetchone()
            if existing:
                version = existing[0] or ""
            else:
                version = "v5.0 test"
                insert(
                    cursor,
                    "omop.vocabulary",
                    returning=None,
                    vocabulary_id=vocabulary_id,
                    vocabulary_name="Carrot test",
                    vocabulary_version=version,
                    vocabulary_concept_id=concepts[0][0],
                )
                cleanup.omop.insert(
                    0, ("omop.vocabulary", "vocabulary_id", vocabulary_id)
                )
        conn.commit()
    except psycopg.Error as e:
        conn.rollback()
        pytest.skip(f"Could not set up OMOP test concepts in this database: {e}")
    return [
        SimpleNamespace(
            id=concept_id, domain=domain, version=version if i == 0 else None
        )
        for i, (concept_id, domain, _) in enumerate(concepts)
    ]


@pytest.fixture
def scan_report(conn, cleanup, user):
    """
    A scan report with one value mapping and one field mapping. Returns
    (id, value_concept, field_concept).
    """
    value_concept_omop, field_concept_omop = omop_concepts(conn, cleanup)
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id FROM django_content_type WHERE app_label = 'mapping' AND model = %s",
            ("scanreportvalue",),
        )
        value_type = cursor.fetchone()[0]
        cursor.execute(
            "SELECT id FROM django_content_type WHERE app_label = 'mapping' AND model = %s",
            ("scanreportfield",),
        )
        field_type = cursor.fetchone()[0]

        def add(table_name, /, **values):
            row_id = insert(cursor, table_name, **values)
            cleanup.rows.append((table_name, row_id))
            return row_id

        # who made the value mapping (the field mapping has no author, like an
        # automatic one): a different user from the publisher, with an ORCID iD
        mapper = insert(cursor, "auth_user", username=f"mapper_{uuid.uuid4().hex[:6]}")
        cleanup.users.append(mapper)
        insert(cursor, "users_profile", user_id=mapper, orcid=AUTHOR_ORCID)

        sr = add(
            "mapping_scanreport", name="sr", dataset="Demo scan report", author_id=user
        )
        table = add(
            "mapping_scanreporttable", scan_report_id=sr, name="demographics.csv"
        )
        sex = add("mapping_scanreportfield", scan_report_table_id=table, name="sex")
        smoker = add(
            "mapping_scanreportfield", scan_report_table_id=table, name="smoker"
        )
        male = add(
            "mapping_scanreportvalue", scan_report_field_id=sex, value="M", conceptID=-1
        )
        omop_table = add("mapping_omoptable", table="person")
        gender_field = add(
            "mapping_omopfield", table_id=omop_table, field="gender_concept_id"
        )
        obs_field = add(
            "mapping_omopfield", table_id=omop_table, field="observation_concept_id"
        )
        value_concept = add(
            "mapping_scanreportconcept",
            concept_id=value_concept_omop.id,
            content_type_id=value_type,
            object_id=male,
            creation_type="M",
            created_by_id=mapper,
        )
        field_concept = add(
            "mapping_scanreportconcept",
            concept_id=field_concept_omop.id,
            content_type_id=field_type,
            object_id=smoker,
            creation_type="V",
        )
        add(
            "mapping_mappingrule",
            scan_report_id=sr,
            concept_id=value_concept,
            omop_field_id=gender_field,
            source_field_id=sex,
        )
        add(
            "mapping_mappingrule",
            scan_report_id=sr,
            concept_id=field_concept,
            omop_field_id=obs_field,
            source_field_id=smoker,
        )
    conn.commit()
    return SimpleNamespace(
        id=sr, value_concept=value_concept_omop, field_concept=field_concept_omop
    )


def test_dag_publishes_a_scan_report(conn, cleanup, user, storage, scan_report):
    job = make_job(conn, cleanup, user, origin="CARROT_DIRECT_PUBLISH")
    set_uri = f"https://carrot.ac.uk/registry/sets/{uuid.uuid4().hex[:8]}"
    terms = "SELECT canonical_iri FROM registry_term"
    before = {r[0] for r in fetch(conn, terms)}

    run_dag(
        {
            "import_job_id": job,
            "origin": "CARROT_DIRECT_PUBLISH",
            "user_id": user,
            "scan_report_id": scan_report.id,
            "mapper_version": "4.3.1",
            # the shape registry.services.submit_direct_publish sends (#1552)
            "overrides": {
                "set_uri": set_uri,
                "set_version": "1",
                "title": "Demo mapping set",
                "description": "",
                "license": "CC-BY-4.0",
                "status": "DRAFT",
                "include_author_orcid_ids": False,
            },
        }
    )
    # only delete the terms this test created, not ones already in the database
    cleanup.terms |= {r[0] for r in fetch(conn, terms)} - before

    row = job_row(conn, job)
    assert row["status"] == "SUCCEEDED", row
    assert row["file_key"] == helpers.file_key_for(job)

    # The stored file is the exporter's, with the set identity from the request
    text = storage.blobs[("registry-sssom", row["file_key"])].decode()
    assert text.startswith(f"#mapping_set_id: {set_uri}\n#mapping_set_version: '1'\n")
    # SPDX's IRI once license_sync has run; a database upgraded from before
    # #1551 keeps the old seeded creativecommons.org IRI until then
    [(license_iri,)] = fetch(
        conn, "SELECT license_iri FROM registry_license WHERE id = 'CC-BY-4.0'"
    )
    assert f"#license: {license_iri}\n" in text
    # the publisher has no ORCID iD, and authors' iDs weren't opted in to
    assert "creator_id" not in text and "author_id" not in text
    assert "orcid" not in text
    # the user's title, not the scan report's name
    assert "#mapping_set_title: Demo mapping set\n" in text
    assert "#mapping_tool_version: 4.3.1\n" in text

    [(status, title, license_id, source_sr, origin)] = fetch(
        conn,
        "SELECT status_id, title, license_id, source_scan_report_id, origin_id "
        "FROM registry_mappingset WHERE import_job_id = %s",
        job,
    )
    assert (status, title, license_id, source_sr, origin) == (
        "DRAFT",
        "Demo mapping set",
        "CC-BY-4.0",
        scan_report.id,
        "CARROT_DIRECT_PUBLISH",
    )
    subjects = fetch(
        conn,
        "SELECT canonical_iri, ext_term_level, ext_source_field, ext_source_value "
        "FROM registry_term WHERE kind = 'SUBJECT' AND canonical_iri IN ('carrot:sex/M', 'carrot:smoker') "
        "ORDER BY canonical_iri",
    )
    assert subjects == [
        ("carrot:sex/M", "VALUE", "sex", "M"),
        ("carrot:smoker", "FIELD", "smoker", ""),
    ]
    # the concept's vocabulary version, from omop.vocabulary
    value_iri = f"OMOP:{scan_report.value_concept.id}"
    if value_iri in cleanup.terms:  # created by this import, not an earlier one
        assert fetch(
            conn,
            "SELECT object_source_version, category FROM registry_term "
            "WHERE canonical_iri = %s AND kind = 'OBJECT'",
            value_iri,
        ) == [(scan_report.value_concept.version, scan_report.value_concept.domain)]
    # the per-job temp rules table is gone
    suffix = helpers.temp_rules_table_suffix(job)
    assert fetch(
        conn,
        "SELECT to_regclass(%s)",
        f"temp_rules_export_{scan_report.id}_{suffix}",
    ) == [(None,)]
    assert (
        notifications(conn, user)[-1][1]
        == "'Demo mapping set' was saved as a draft in the mappings registry"
    )


@pytest.mark.parametrize("include_author_orcid_ids", [False, True])
def test_dag_publishes_creator_orcid_and_authors_only_when_opted_in(
    conn, cleanup, user, storage, scan_report, include_author_orcid_ids
):
    with conn.cursor() as cursor:
        insert(cursor, "users_profile", user_id=user, orcid=PUBLISHER_ORCID)
    conn.commit()
    terms = "SELECT canonical_iri FROM registry_term"
    before = {r[0] for r in fetch(conn, terms)}
    job = make_job(conn, cleanup, user, origin="CARROT_DIRECT_PUBLISH")

    run_dag(
        {
            "import_job_id": job,
            "origin": "CARROT_DIRECT_PUBLISH",
            "user_id": user,
            "scan_report_id": scan_report.id,
            "overrides": {
                "set_uri": f"https://carrot.ac.uk/sssom/mapping-sets/{uuid.uuid4().hex}",
                "set_version": "1",
                "title": "With ORCID",
                "license": "CC-BY-4.0",
                "include_author_orcid_ids": include_author_orcid_ids,
            },
        }
    )
    cleanup.terms |= {r[0] for r in fetch(conn, terms)} - before

    row = job_row(conn, job)
    assert row["status"] == "SUCCEEDED", row
    text = storage.blobs[("registry-sssom", row["file_key"])].decode()

    # the publisher (creator) is always named, with their ORCID iD
    assert f"#creator_id:\n#- orcid:{PUBLISHER_ORCID}\n" in text
    assert fetch(
        conn,
        "SELECT creator_ids FROM registry_mappingset WHERE import_job_id = %s",
        job,
    ) == [([f"orcid:{PUBLISHER_ORCID}"],)]

    # each mapping's author only when opted in; the field mapping has none
    authors = fetch(
        conn,
        "SELECT s.canonical_iri, m.author_ids FROM registry_mapping m "
        "JOIN registry_mappingset ms ON ms.id = m.mapping_set_id "
        "JOIN registry_term s ON s.id = m.subject_id "
        "WHERE ms.import_job_id = %s ORDER BY s.canonical_iri",
        job,
    )
    if include_author_orcid_ids:
        header = next(line for line in text.splitlines() if not line.startswith("#"))
        assert "author_id" in header.split("\t")
        assert authors == [
            ("carrot:sex/M", [f"orcid:{AUTHOR_ORCID}"]),
            ("carrot:smoker", []),
        ]
    else:
        assert "author_id" not in text and AUTHOR_ORCID not in text
        assert authors == [("carrot:sex/M", []), ("carrot:smoker", [])]


def test_dag_fails_cleanly_for_a_scan_report_without_mappings(
    conn, cleanup, user, storage
):
    with conn.cursor() as cursor:
        sr = insert(
            cursor, "mapping_scanreport", name="empty", dataset="Empty", author_id=user
        )
    conn.commit()
    cleanup.rows.append(("mapping_scanreport", sr))
    job = make_job(conn, cleanup, user, origin="CARROT_DIRECT_PUBLISH")

    with pytest.raises(AirflowFailException, match="no mappings to publish"):
        run_dag(
            {
                "import_job_id": job,
                "origin": "CARROT_DIRECT_PUBLISH",
                "user_id": user,
                "scan_report_id": sr,
                "overrides": {
                    "set_uri": "https://x.org/s",
                    "set_version": "1",
                    "title": "Empty",
                    "license": "CC-BY-4.0",
                    "include_author_orcid_ids": False,
                },
            }
        )
    row = job_row(conn, job)
    assert row["status"] == "FAILED" and "no mappings" in row["error"]

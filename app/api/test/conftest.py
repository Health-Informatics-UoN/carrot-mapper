from collections.abc import Generator

import psycopg2
import pytest
from data.models import Concept, ConceptRelationship, Vocabulary
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pytest_django import DjangoDbBlocker


def run_sql(db: str, sql: str):
    """
    Executes the given SQL query on the given database.

    Args:
        db: The name of the database to connect to.
        sql: The SQL query to execute.

    Returns:
        None

    Raises:
        psycopg2.Error: If there is an error executing the SQL.
    """
    conn = psycopg2.connect(
        dbname=db,
        user=settings.DATABASES["default"]["USER"],
        password=settings.DATABASES["default"]["PASSWORD"],
        host=settings.DATABASES["default"]["HOST"],
        port=settings.DATABASES["default"]["PORT"],
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(sql)
    conn.close()


@pytest.fixture(scope="session")
def django_db_setup(
    django_db_blocker: DjangoDbBlocker,
    django_db_keepdb: bool,
) -> Generator[None, None, None]:
    """
    Override Pytest db setup, to create the OMOP schema and tables.

    This is necessary for the migrations to run successfully in test,
    as the migrations depend on this schema/tables existing.
    """
    # Set the default db to the test one for ease.
    db_name = settings.DATABASES["default"]["TEST"]["NAME"]

    # Manually create the test DB + omop Schema if it doesn't exist, drop if it does.
    run_sql("postgres", f"DROP DATABASE IF EXISTS {db_name}")
    run_sql("postgres", f"CREATE DATABASE {db_name} TEMPLATE template0")
    run_sql(db_name, "CREATE SCHEMA IF NOT EXISTS omop")
    # Needed for trigram_similar/TrigramSimilarity lookups used by concept search.
    run_sql(db_name, "CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Set the default to test for ease
    settings.DATABASES["default"]["NAME"] = db_name

    # Create all the OMOP tables that might be referenced during tests
    omop_models = [Concept, ConceptRelationship, Vocabulary]

    with django_db_blocker.unblock():
        with connection.schema_editor() as schema_editor:
            for model in omop_models:
                schema_editor.create_model(model)

        # ConceptSynonym's model declares `concept_id` as its Django pk (a
        # single field is required), but the real OMOP table's primary key
        # is the composite (concept_id, concept_synonym_name,
        # language_concept_id) -- a concept has many synonyms. Creating it
        # via schema_editor.create_model would wrongly make concept_id
        # unique, so it's created with raw DDL matching the real schema
        # instead; ORM reads/writes via `.filter()`/`.values()`/`.create()`
        # don't depend on which column Django considers the pk.
        run_sql(
            db_name,
            """
            CREATE TABLE IF NOT EXISTS "omop"."concept_synonym" (
                concept_id integer NOT NULL,
                concept_synonym_name varchar(1000) NOT NULL,
                language_concept_id integer NOT NULL,
                PRIMARY KEY (concept_id, concept_synonym_name, language_concept_id)
            )
            """,
        )

        # run the rest of the migrations
        call_command("migrate", "--noinput")

    yield

    # If not keeping the test db, drop it
    if not django_db_keepdb:
        run_sql("postgres", f"DROP DATABASE {db_name}")

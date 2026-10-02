from airflow.providers.postgres.hooks.postgres import USE_PSYCOPG3, PostgresHook

from libs.settings import AIRFLOW_DAGRUN_TIMEOUT


class ClientSidePostgresHook(PostgresHook):
    """
    PostgresHook that binds query parameters client-side.

    With SQLAlchemy 2 installed, PostgresHook uses psycopg3, which binds parameters
    server-side. That breaks our queries that build table names from parameters
    (e.g. temp_field_values_%(table_id)s) and that run several statements with
    parameters in one call. psycopg3's ClientCursor keeps psycopg2's behaviour.
    """

    def get_conn(self):
        conn = super().get_conn()
        if USE_PSYCOPG3:
            from psycopg import ClientCursor

            conn.cursor_factory = ClientCursor
        return conn


# PostgreSQL connection hook
pg_hook = ClientSidePostgresHook(
    postgres_conn_id="postgres_db_conn",
    options=f"-c statement_timeout={float(AIRFLOW_DAGRUN_TIMEOUT) * 60 * 1000}ms",
)

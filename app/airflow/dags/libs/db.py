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

    def get_sqlalchemy_engine(self, engine_kwargs=None):
        # get_pandas_df/get_df connect through SQLAlchemy rather than get_conn(),
        # so the cursor factory has to be passed to the engine as well.
        if USE_PSYCOPG3:
            from psycopg import ClientCursor

            engine_kwargs = dict(engine_kwargs or {})
            connect_args = dict(engine_kwargs.get("connect_args", {}))
            connect_args.setdefault("cursor_factory", ClientCursor)
            engine_kwargs["connect_args"] = connect_args
        return super().get_sqlalchemy_engine(engine_kwargs=engine_kwargs)


# PostgreSQL connection hook
pg_hook = ClientSidePostgresHook(
    postgres_conn_id="postgres_db_conn",
    options=f"-c statement_timeout={float(AIRFLOW_DAGRUN_TIMEOUT) * 60 * 1000}ms",
)

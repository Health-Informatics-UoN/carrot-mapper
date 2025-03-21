from datetime import timedelta, datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from libs.core import save_data, generate_sql

# TODO: Check and make more configurable settings from env.
default_args = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": None,  # Add a failure callback function here
}

with DAG(
    "simple-extractor-postgres",
    default_args=default_args,
    start_date=datetime(2025, 1, 30),
    description="Extract data from database to CSV",
    schedule_interval=None,
    catchup=False,
    render_template_as_native_obj=True,
) as dag:
    generate_sql = PythonOperator(
        task_id="generate_sql",
        python_callable=generate_sql,
        provide_context=True,
        retries=1,
        retry_delay=timedelta(minutes=1),
    )

    get_headers = SQLExecuteQueryOperator(
        task_id="get_headers",
        sql="sql/sql_headers_query.sql",
        conn_id="1-connection",
        database="postgres",
        retries=1,
        retry_delay=timedelta(minutes=1),
    )

    get_data = SQLExecuteQueryOperator(
        task_id="get_data",
        sql="sql/sql_data_query.sql",
        conn_id="1-connection",
        database="postgres",
        retries=1,
        retry_delay=timedelta(minutes=1),
    )

    save_data = PythonOperator(
        task_id="save_data",
        python_callable=save_data,
        provide_context=True,
        retries=1,
        retry_delay=timedelta(minutes=1),
    )

    generate_sql >> get_headers >> get_data >> save_data

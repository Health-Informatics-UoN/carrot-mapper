FROM apache/airflow:2.6.1

# Install provider packages
RUN pip install --no-cache-dir \
    apache-airflow-providers-microsoft-azure \
    apache-airflow-providers-postgres \
    apache-airflow-providers-amazon \
    apache-airflow-providers-http

# Copy DAGs to the container
COPY ./dags /opt/airflow/dags

# Set ownership of copied files
USER root
RUN chown -R airflow:root /opt/airflow/dags
USER airflow



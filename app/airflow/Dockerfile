# TODO: Airflow has version 3.0.0 but this is a breaking change
FROM apache/airflow:2.10.5

# Build argument to determine which entrypoint to use
ARG AIRFLOW_COMPONENT=webserver

# Install provider packages
RUN pip install --no-cache-dir \
    apache-airflow-providers-microsoft-azure \
    apache-airflow-providers-postgres \
    apache-airflow-providers-amazon \
    openpyxl \
    types-openpyxl \
    types-psycopg2 \
    pandas \
    pandas-stubs

# Copy DAGs to the container
COPY --chown=airflow:root ./dags /opt/airflow/dags

# Create directories with correct ownership
USER root
RUN mkdir -p /opt/airflow/logs /opt/airflow/config && \
    chown -R airflow:root /opt/airflow && \
    chmod -R g+rw /opt/airflow

# Copy and setup entrypoint script based on component
COPY --chown=airflow:root entrypoint-${AIRFLOW_COMPONENT}.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER airflow

# Set umask to ensure new files are group writable
ENV UMASK=0002

ENTRYPOINT ["/entrypoint.sh"]
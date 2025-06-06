# TODO: Airflow has version 3.0.0 but this is a breaking change
FROM apache/airflow:2.10.5

# Build argument to determine which entrypoint to use
ARG AIRFLOW_COMPONENT=webserver

# Switch to root for system-level operations
USER root

# Create directories with correct ownership early
RUN mkdir -p /opt/airflow/logs /opt/airflow/config && \
    chown -R airflow:root /opt/airflow && \
    chmod -R g+rw /opt/airflow

# Copy and setup entrypoint script based on component
COPY --chown=airflow:root entrypoint-${AIRFLOW_COMPONENT}.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch back to airflow user for package installation
USER airflow

# Copy requirements and install dependencies in a single layer
COPY --chown=airflow:root requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Copy DAGs to the container
COPY --chown=airflow:root ./dags /opt/airflow/dags

# Set umask to ensure new files are group writable
ENV UMASK=0002

ENTRYPOINT ["/entrypoint.sh"]
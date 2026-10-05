FROM apache/airflow:3.3.2

# Build argument to determine which entrypoint to use
ARG AIRFLOW_COMPONENT=webserver

# Version is resolved from git tags by CI (semantic-release) and passed in here.
# Unlike the API image, the local carrot-airflow project isn't pip-installed into
# this image (see below), so there's no package metadata for setuptools_scm to bake
# in - the version is just carried as a label/env var instead.
ARG AIRFLOW_APP_VERSION=0.0.0.dev0
ENV AIRFLOW_APP_VERSION=${AIRFLOW_APP_VERSION}
LABEL org.opencontainers.image.version=${AIRFLOW_APP_VERSION}

# Install provider packages 
RUN pip install --no-cache-dir \
    "apache-airflow-providers-microsoft-azure==15.1.0" \
    "apache-airflow-providers-postgres==7.0.2" \
    "apache-airflow-providers-amazon==9.36.0" \
    "apache-airflow-providers-keycloak==0.10.0" \
    "openpyxl==3.1.5" \
    "pandas==3.0.5"

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
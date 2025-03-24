FROM apache/airflow:2.6.1

USER root
# TODO: revert to the Postgres install
# Install dependencies including FreeTDS and OpenSSL
RUN apt-get update && \
    apt-get install -y build-essential unixodbc-dev curl apt-transport-https gnupg \
    freetds-dev freetds-bin openssl libssl-dev && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 mssql-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow
# Install pymssql with proper linking to FreeTDS and OpenSSL
ENV LDFLAGS="-L/usr/lib/x86_64-linux-gnu"
ENV CFLAGS="-I/usr/include/freetds"
RUN pip install --no-cache-dir pymssql==2.1.5 pyodbc apache-airflow-providers-microsoft-mssql

USER airflow

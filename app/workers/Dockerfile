# To enable ssh & remote debugging on app service change the base image to the one below
# FROM mcr.microsoft.com/azure-functions/python:4-python3.11-appservice
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

USER root
RUN mkdir /workers
WORKDIR /workers

COPY ./workers/pyproject.toml /workers/pyproject.toml
COPY ./workers/uv.lock /workers/uv.lock

# Copy the shared directory
COPY ./shared /shared

# Install UV & export requirements from pyproject.toml and install them
RUN pip install uv && \
    uv pip compile pyproject.toml --output-file requirements.txt && \
    uv pip install --no-cache-dir -r requirements.txt --system

RUN chmod u+x /workers
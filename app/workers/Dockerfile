# To enable ssh & remote debugging on app service change the base image to the one below
# FROM mcr.microsoft.com/azure-functions/python:4-python3.11-appservice
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

USER root
RUN mkdir /workers
WORKDIR /workers

COPY ./workers/pyproject.toml /workers/pyproject.toml
COPY ./workers/poetry.lock /workers/poetry.lock

# Copy the shared directory
COPY ./shared /shared

# Install Poetry and Export Poetry Plugin
RUN pip install poetry
RUN pip install poetry-plugin-export

# Export requirements from pyproject.toml and install them
RUN poetry config virtualenvs.create false \
    && poetry export --format requirements.txt --output /workers/requirements.txt --without-hashes \
    && pip install --no-cache-dir -r /workers/requirements.txt

RUN chmod u+x /workers
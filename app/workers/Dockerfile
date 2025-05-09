# To enable ssh & remote debugging on app service change the base image to the one below
# FROM mcr.microsoft.com/azure-functions/python:4-python3.11-appservice

# ----------------------------
# Stage 1: Builder
# ----------------------------
FROM mcr.microsoft.com/azure-functions/python:4-python3.11-slim AS builder

WORKDIR /workers
COPY ./workers/pyproject.toml ./api/uv.lock /workers/
COPY ./shared /shared

# ---- Install uv & Dependencies & Remove caches & tooling artefacts
RUN pip install uv && \ 
    uv pip compile pyproject.toml --output-file requirements.txt && \
    uv pip install --no-cache-dir -r requirements.txt --system && \
    rm -rf /root/.cache /root/.cargo /root/.rustup /root/.config

# ----------------------------
# Stage 2: Runtime 
# ----------------------------
FROM mcr.microsoft.com/azure-functions/python:4-python3.11-slim

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

WORKDIR /workers

# Bring in dependencies built in the previous stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code and shared modules
COPY ./workers ./shared /

# Remove the default requirements.txt file (If possible)
COPY --from=builder /workers/requirements.txt /workers/requirements.txt 
RUN chmod +x /workers
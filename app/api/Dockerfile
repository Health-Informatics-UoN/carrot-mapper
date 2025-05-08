# ----------------------------
# Stage 1: Builder
# ----------------------------
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# --- Create 'django' user and set up app directory 
RUN addgroup -q django && \
    adduser --quiet --ingroup django --disabled-password django

COPY --chown=django:django ./api /api
WORKDIR /api

USER django
ENV PATH=/home/django/.local/bin:$PATH

# --- Copy files needed for compilation and shared resources
COPY ./shared /shared

# ---- Install Dependencies using UV & Remove caches & tooling artefacts
USER root
RUN uv pip install --no-cache-dir --system . && \
    rm -rf /root/.cargo /root/.rustup

# ----------------------------
# Stage 2: Runtime
# ----------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1
EXPOSE 8000
WORKDIR /api

RUN  apt-get update && apt-get install -y --no-install-recommends\
    wait-for-it \
    graphviz \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Copy required dirs from builder (includes libs, user info, and code)

# 1. Python packages + CLI entry-points
COPY --from=builder /usr/local/lib/python3.11/site-packages \
                    /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 2. Application code & Shared modules
COPY --from=builder /api /api
COPY --from=builder /shared /shared

# 3. User / Group definitions for Django 
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

# --- Entrypoint Execution setup
COPY --chown=django:django --chmod=0755 ./api/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Return to django user to run the container as this user by default
USER django

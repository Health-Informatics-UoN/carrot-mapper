# ----------------------------
# Stage 1: Builder
# ----------------------------
FROM python:3.11-slim AS builder

# --- Install OS packages & uv
RUN apt-get update && \
    apt-get install -y \
        binutils \
        gettext \
        libpq-dev \
        gcc \
        graphviz && \
    pip install --no-cache-dir uv 

# --- Install rustup (needed for some cryptography packages)
RUN curl -y --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# --- Create 'django' user and set up app directory 
RUN addgroup -q django && \
    adduser --quiet --ingroup django --disabled-password django

COPY ./api /api
WORKDIR /api
RUN chown -R django:django /api

USER django
ENV PATH=/home/django/.local/bin:$PATH

# --- Copy files needed for compilation and shared resources
COPY ./api/pyproject.toml ./api/uv.lock /api/
COPY ./shared /shared

# --- Compile dependencies using UV and install them 
USER root
RUN uv pip compile pyproject.toml --output-file requirements.txt && \
    uv pip install --no-cache-dir -r requirements.txt --system && \
    rm -rf /root/.cargo /root/.rustup

# ----------------------------
# Stage 2: Runtime
# ----------------------------
FROM python:3.11-slim
LABEL authors="Roberto Santos"

ENV PYTHONUNBUFFERED 1
EXPOSE 8000
WORKDIR /api

RUN  apt-get update && apt-get install -y --no-install-recommends\
    wait-for-it \
    libpq5 \
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

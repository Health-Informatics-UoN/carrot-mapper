# ----------------------------
# Stage 1: Builder
# ----------------------------
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# --- Create 'django' user and set up app directory
RUN addgroup -q django && \
    adduser --quiet --ingroup django --disabled-password django

# git is needed so hatch-vcs (via setuptools_scm) can resolve the package
# version from tags in .git below - see app/api/pyproject.toml.
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copied to /app/api (not /api) to preserve the same two-directory nesting
# under .git as the real repo, matching pyproject.toml's `root = "../.."`.
COPY --chown=django:django ./app/api /app/api
# Build context is the monorepo root (not ./app/api) so .git is available
# here. hatch-vcs walks up from pyproject.toml via `root = "../.."` to find
# it and resolve the version dynamically from git tags - no version needs to
# be passed in from CI. If .git is ever unavailable in the build context,
# `fallback-version` in pyproject.toml is used instead.
COPY ./.git /.git
WORKDIR /app/api

USER django
ENV PATH=/home/django/.local/bin:$PATH

# ---- Install Dependencies using UV & Remove caches & tooling artefacts
USER root

RUN git config --global --add safe.directory / && \
    uv pip install --no-cache-dir --system . && \
    rm -rf /root/.cargo /root/.rustup

# ----------------------------
# Stage 2: Runtime
# ----------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
WORKDIR /api

RUN  apt-get update && apt-get install -y --no-install-recommends\
    wait-for-it \
    graphviz \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Copy required dirs from builder (includes libs, user info, and code)

# 1. Python packages + CLI entry-points
COPY --from=builder /usr/local/lib/python3.11/site-packages \
                    /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 2. Application code
COPY --from=builder /app/api /api

# 3. User / Group definitions for Django 
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

# --- Entrypoint Execution setup
COPY --chown=django:django --chmod=0755 ./app/api/entrypoint.sh /entrypoint.sh
RUN mkdir -p /api/staticfiles && \
    chown -R django:django /api/staticfiles && \
    chmod 755 /api/staticfiles
ENTRYPOINT ["/entrypoint.sh"]

# Return to django user to run the container as this user by default
USER django

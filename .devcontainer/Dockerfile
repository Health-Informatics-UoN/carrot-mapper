# Dev container image for running the API and frontend from source (see
# CONTRIBUTING.md). This is NOT the production API image
# (app/api/Dockerfile) - it just needs uv/Python and Node in one place, plus
# the system packages the API needs at runtime (git for hatch-vcs
# versioning, graphviz for the `graphviz` Python bindings).
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    graphviz \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

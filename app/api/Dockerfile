FROM python:3.11-slim
LABEL authors="Roberto Santos"

ENV PYTHONUNBUFFERED 1

EXPOSE 8000

RUN apt-get update && \
    apt-get install -y \
        vim \
        htop \
        wait-for-it \
        binutils \
        gettext \
        libpq-dev \
        gcc \
        graphviz \
        git

# Install rustup to allow install of cryptography package
RUN curl -y --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Create django user
RUN addgroup -q django && \
    adduser --quiet --ingroup django --disabled-password django

# Create /api directory for mounting
COPY ./api /api
WORKDIR /api
RUN chown -R django:django /api

# Install PyPI packages as django user
USER django
ENV PATH=/home/django/.local/bin:$PATH

# Copy pyproject.toml
COPY ./api/pyproject.toml ./api/pyproject.toml
COPY ./api/uv.lock ./api/uv.lock

# Copy shared package
COPY ./shared /shared

USER root
RUN pip install uv
RUN uv pip compile pyproject.toml --output-file requirements.txt && \
    uv pip install --no-cache-dir -r requirements.txt --system

# Copy entrypoint as root, elevate it to executable, then give it over to django user
COPY ./api/entrypoint.sh /entrypoint.sh
RUN chmod u+x /entrypoint.sh
RUN chown -R django:django /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Return to django user to run the container as this user by default
USER django

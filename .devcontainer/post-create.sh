#!/usr/bin/env bash
# One-time dev container setup. Mirrors the "first time you bring the stack
# up" steps in CONTRIBUTING.md - see that file for what each step does and
# why the order matters.
set -euo pipefail

cd /workspaces/carrot-mapper

[ -f .env ] || cp .env.example .env
[ -f app/next-client-app/.env ] || cp app/next-client-app/.env.example app/next-client-app/.env

# Use the azurite profile, not minio: minio and azurite are alternatives
# (STORAGE_TYPE picks one), and minio/minio isn't reliably pullable from
# Docker Hub inside a Codespace, while azurite's mcr.microsoft.com image is.
sed -i "s#^COMPOSE_PROFILES=.*#COMPOSE_PROFILES=azure#" .env
sed -i "s#^STORAGE_TYPE=.*#STORAGE_TYPE=azure#" .env

# Running in a GitHub Codespace: the browser reaches the frontend through
# the forwarded https URL, not localhost, so NextAuth and the API's CORS
# allow-list need to know that URL too.
if [ "${CODESPACES:-}" = "true" ]; then
  PUBLIC_URL="https://${CODESPACE_NAME}-3000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
  sed -i "s#^FRONTEND_URL=.*#FRONTEND_URL=${PUBLIC_URL}#" .env
  sed -i "s#^NEXTJS_URL=.*#NEXTJS_URL=${PUBLIC_URL}#" .env
  sed -i "s#^NEXTAUTH_URL=.*#NEXTAUTH_URL=${PUBLIC_URL}/#" app/next-client-app/.env
fi

# db is already up (devcontainer.json's runServices); start the one-shot
# OMOP vocab loader and azurite, and wait for the vocab loader to finish
# before the API creates the Airflow schema below.
docker compose up -d db omop-lite azurite
docker wait "$(docker compose ps -q omop-lite)"

# Bootstrap the API from source.
(
  cd app/api
  uv sync
  uv run manage.py airflow_schema_creation
  uv run manage.py migrate
  uv run manage.py automatic_seeding_data
  uv run manage.py default_super_user
  uv run manage.py automatic_queue_and_containers_creation
)

# Now that the Airflow schema exists, bring up the rest of the stack.
docker compose up -d

# Frontend dependencies.
(
  cd app/next-client-app
  npm install
)

cat <<'EOF'

Setup complete. In two terminals:
  cd app/api && uv run manage.py runserver
  cd app/next-client-app && npm run dev

Ports 3000 (frontend), 8000 (API) and 8080 (Airflow) are forwarded
automatically.
EOF

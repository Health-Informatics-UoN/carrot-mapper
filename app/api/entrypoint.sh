#!/bin/bash

# Wait until DB is available
wait-for-it ${DB_HOST}:${DB_PORT} -- echo "Database is ready! Listening on ${DB_HOST}:${DB_PORT}"


# Collect static files for serving
python manage.py airflow_schema_creation
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py automatic_seeding_data
python manage.py default_super_user
python manage.py automatic_queue_and_containers_creation

# Set tmp dir to be in-memory for speed. Pass logs to stdout/err as Docker will expect them there.
# gthread workers let each process serve several requests concurrently, so one slow
# request (e.g. a large scan report page) doesn't block the others.
gunicorn --config gunicorn.conf.py \
  --worker-tmp-dir /dev/shm \
  --worker-class gthread \
  --workers ${GUNICORN_WORKERS:-5} \
  --threads ${GUNICORN_THREADS:-5} \
  --timeout ${GUNICORN_TIMEOUT:-600} \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile - \
  --bind :8000 \
  config.wsgi:application

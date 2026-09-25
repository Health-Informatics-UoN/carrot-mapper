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

# Backgrounded, not sequential like the commands above: building the GIN
# trigram indexes over the full vocab can take several minutes, and
# blocking here would delay gunicorn past Azure's container startup/health
# check window on the first deploy after this ships. Safe to leave running
# on every start -- CREATE INDEX CONCURRENTLY IF NOT EXISTS is a fast no-op
# once the indexes already exist. Search is just unaccelerated (slower, not
# broken) until this finishes.
python manage.py setup_search_indexes &

# Set tmp dir to be in-memory for speed. Pass logs to stdout/err as Docker will expect them there
gunicorn --config gunicorn.conf.py --worker-tmp-dir /dev/shm --timeout 600 --log-file=- --bind :8000 --workers 3 config.wsgi:application --reload

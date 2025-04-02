#!/bin/bash

# Wait until DB is available
wait-for-it ${DB_HOST}:${DB_PORT} -- echo "Database is ready! Listening on ${DB_HOST}:${DB_PORT}"


# Collect static files for serving
rm -rf staticfiles
mkdir staticfiles
python manage.py collectstatic
python manage.py migrate
python manage.py automatic_seeding_data
python manage.py default_super_user
python manage.py automatic_queue_and_containers_creation

# Set tmp dir to be in-memory for speed. Pass logs to stdout/err as Docker will expect them there
gunicorn --config gunicorn.conf.py --worker-tmp-dir /dev/shm --timeout 600 --log-file=- --bind :8000 --workers 3 config.wsgi:application --reload

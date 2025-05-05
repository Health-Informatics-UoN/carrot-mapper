#!/bin/bash
set -e

# TODO: clean up the procedure of finding the airflow executable
# Try to find the airflow executable
echo "Searching for airflow executable..."
AIRFLOW_PATHS=(
  "/home/airflow/.local/bin/airflow"
  "/usr/local/bin/airflow"
  "/usr/local/sbin/airflow"
  "/usr/bin/airflow"
  "/usr/sbin/airflow"
  "/opt/airflow/bin/airflow"
  "/opt/airflow/airflow"
  "/root/bin/airflow"
)

AIRFLOW_EXEC=""
for path in "${AIRFLOW_PATHS[@]}"; do
  if [ -f "$path" ]; then
    echo "Found airflow at: $path"
    AIRFLOW_EXEC="$path"
    break
  fi
done

# If not found in common locations, search the system
if [ -z "$AIRFLOW_EXEC" ]; then
  echo "Airflow not found in common locations, searching system..."
  FOUND_PATH=$(find / -name "airflow" -type f -executable 2>/dev/null | head -1)
  if [ -n "$FOUND_PATH" ]; then
    echo "Found airflow at: $FOUND_PATH"
    AIRFLOW_EXEC="$FOUND_PATH"
  fi
fi

# Exit if airflow still not found
if [ -z "$AIRFLOW_EXEC" ]; then
  echo "ERROR: Could not locate airflow executable anywhere on the system"
  echo "Checking if 'airflow' is available in PATH..."
  which airflow || echo "airflow not in PATH"
  exit 1
fi

# Wait for the database to be ready
$AIRFLOW_EXEC db check || { echo "Database check failed"; exit 1; }

# Initialize/upgrade the database
$AIRFLOW_EXEC db migrate || { echo "Database migrate failed"; exit 1; }

# Set default values for environment variables if not provided
AIRFLOW_ADMIN_USERNAME=${AIRFLOW_ADMIN_USERNAME:-admin}
AIRFLOW_ADMIN_PASSWORD=${AIRFLOW_ADMIN_PASSWORD:-admin}
AIRFLOW_ADMIN_FIRSTNAME=${AIRFLOW_ADMIN_FIRSTNAME:-Air}
AIRFLOW_ADMIN_LASTNAME=${AIRFLOW_ADMIN_LASTNAME:-Flow}
AIRFLOW_ADMIN_EMAIL=${AIRFLOW_ADMIN_EMAIL:-admin@example.com}
AIRFLOW_ADMIN_ROLE=${AIRFLOW_ADMIN_ROLE:-Admin}

# Create admin user with correct command syntax
$AIRFLOW_EXEC users create \
  --username "$AIRFLOW_ADMIN_USERNAME" \
  --password "$AIRFLOW_ADMIN_PASSWORD" \
  --firstname "$AIRFLOW_ADMIN_FIRSTNAME" \
  --lastname "$AIRFLOW_ADMIN_LASTNAME" \
  --role "$AIRFLOW_ADMIN_ROLE" \
  --email "$AIRFLOW_ADMIN_EMAIL"

# Start the webserver
$AIRFLOW_EXEC webserver
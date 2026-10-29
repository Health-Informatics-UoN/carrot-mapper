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

# Run the dag-processor and scheduler
$AIRFLOW_EXEC dag-processor &
DAG_PROCESSOR_PID=$!
$AIRFLOW_EXEC scheduler &
SCHEDULER_PID=$!

stop_children() {
  kill -TERM "$DAG_PROCESSOR_PID" "$SCHEDULER_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}

# Forward termination (e.g. Azure stopping the app) to both processes
trap 'stop_children; exit 0' TERM INT

# If either process dies, stop the other and exit non-zero so Azure restarts the container
EXIT_CODE=0
wait -n || EXIT_CODE=$?
echo "A child process exited (code ${EXIT_CODE}), shutting down"
stop_children
[ "$EXIT_CODE" -eq 0 ] && EXIT_CODE=1
exit "$EXIT_CODE"

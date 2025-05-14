from enum import StrEnum


class WorkerServiceType(StrEnum):
    """Enum for worker service types."""

    AZURE = "azure"
    AIRFLOW = "airflow"

from enum import StrEnum


class WorkerServiceType(StrEnum):
    """Enum for worker service types."""

    AIRFLOW = "airflow"


class ContentTypeModel(StrEnum):
    """Enum for content type models."""

    SCAN_REPORT_VALUE = "scanreportvalue"
    SCAN_REPORT_FIELD = "scanreportfield"

from enum import StrEnum


class StorageType(StrEnum):
    AZURE = "azure"
    MINIO = "minio"


class StageStatusType(StrEnum):
    IN_PROGRESS = "Job in Progress"
    COMPLETE = "Job Complete"
    FAILED = "Job Failed"


class JobStageType(StrEnum):
    UPLOAD_SCAN_REPORT = "Upload Scan Report"
    BUILD_CONCEPTS_FROM_DICT = "Build concepts from OMOP Data dictionary"
    REUSE_CONCEPTS = "Reuse concepts from other scan reports"
    GENERATE_RULES = "Generate mapping rules from available concepts"
    GENERATE_AI_RECOMMENDATIONS = "Generate AI-powered mapping recommendations"
    DOWNLOAD_RULES = "Generate and download mapping rules JSON"

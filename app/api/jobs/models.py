from django.db import models
from mapping.models import BaseModel, ScanReport, ScanReportTable


class JobStage(models.Model):
    value = models.CharField(max_length=64)
    display_name = models.CharField(max_length=64)


class StageStatus(models.Model):
    value = models.CharField(max_length=64)
    display_name = models.CharField(max_length=64)


class Job(BaseModel):
    scan_report = models.ForeignKey(
        ScanReport,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="scan_report",
    )
    scan_report_table = models.ForeignKey(
        ScanReportTable,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="scan_report_table",
    )
    stage = models.ForeignKey(
        "JobStage",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
        related_name="job_stage",
    )
    status = models.ForeignKey(
        "StageStatus",
        null=True,
        blank=True,
        on_delete=models.DO_NOTHING,
        related_name="stage_status",
    )
    details = models.TextField(null=True, blank=True)

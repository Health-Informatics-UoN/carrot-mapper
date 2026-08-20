from django.conf import settings
from django.db import models
from django.utils import timezone
from mapping.models import BaseModel


class ScopeType(models.TextChoices):
    SCAN_REPORT = "scanreport", "Scan Report"
    DATASET = "dataset", "Dataset"


class Verb(models.TextChoices):
    SCAN_REPORT_UPLOADED = "scanreport.uploaded", "Scan report uploaded"
    SCAN_REPORT_UPDATED = "scanreport.updated", "Scan report updated"
    DATASET_UPDATED = "dataset.updated", "Dataset updated"
    MAPPING_ADDED = "mapping.added", "Mapping added"
    MAPPING_DELETED = "mapping.deleted", "Mapping deleted"
    RULES_EXPORT_REQUESTED = "rules.export_requested", "Rules export requested"
    RULES_DOWNLOADED = "rules.downloaded", "Rules downloaded"
    AUTOMAP_RAN = "automap.ran", "Auto mapping ran"


class ActivityLog(BaseModel):
    """
    An append-only record of a human-triggered event on a Scan Report or
    Dataset (e.g. a mapping being added, rules being downloaded).

    No GenericForeignKey is used for `object_type`/`object_id`: events must
    still be visible after the object they reference has been deleted, so
    the reference is a plain type+id pair resolved at render time instead.
    """

    scope_type = models.CharField(max_length=32, choices=ScopeType.choices)
    scope_id = models.IntegerField()
    verb = models.CharField(max_length=64, choices=Verb.choices)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    # Snapshot of the actor's username, taken at write time, so the log
    # entry still reads sensibly after the user has been deprovisioned.
    actor_label = models.CharField(max_length=150)

    object_type = models.CharField(max_length=32, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = "activity_log"
        indexes = [
            models.Index(
                fields=["scope_type", "scope_id", "-occurred_at"],
                name="idx_activitylog_scope",
            ),
        ]

    def __str__(self):
        return str(self.id)

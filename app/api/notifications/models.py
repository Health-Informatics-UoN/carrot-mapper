from django.conf import settings
from django.db import models

from mapping.models import BaseModel


class NotificationType(models.TextChoices):
    SCAN_REPORT_PROCESSING_COMPLETE = (
        "scanreport.processing_complete",
        "Scan report processing complete",
    )
    SCAN_REPORT_PROCESSING_FAILED = (
        "scanreport.processing_failed",
        "Scan report processing failed",
    )
    AUTOMAP_COMPLETE = "automap.complete", "Auto mapping complete"
    AUTOMAP_FAILED = "automap.failed", "Auto mapping failed"
    RULES_EXPORT_COMPLETE = "rules.export_complete", "Rules export complete"
    RULES_EXPORT_FAILED = "rules.export_failed", "Rules export failed"
    BROADCAST = "broadcast", "Broadcast announcement"


class Notification(BaseModel):
    """
    A single notification delivered to one recipient. Broadcasts are
    fanned out to one row per active user at write time, rather than
    normalized behind a join table, matching the append-only,
    denormalized-for-simplicity style already used by ActivityLog.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    notif_type = models.CharField(max_length=64, choices=NotificationType.choices)
    text = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True)
    # Nullable timestamp rather than a bare boolean: doubles as both the
    # "read" and "dismissed" state from the feature's acceptance criteria,
    # since this feature doesn't need to distinguish the two.
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["recipient", "-created_at"],
                name="idx_notification_recipient",
            ),
        ]

    def __str__(self):
        return str(self.id)


class BroadcastAnnouncement(BaseModel):
    """
    Admin-only record of a mapper-wide announcement. Creating one (via
    Django admin) fans out a Notification to every active user - see
    notifications.admin.BroadcastAnnouncementAdmin.save_model.
    """

    text = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        app_label = "notifications"

    def __str__(self):
        return self.text

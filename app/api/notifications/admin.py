from django.contrib import admin

from services.notifications import broadcast

from .models import BroadcastAnnouncement, Notification, NotificationType


class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "notif_type", "text", "created_at", "read_at")
    list_filter = ("notif_type",)
    raw_id_fields = ("recipient",)


class BroadcastAnnouncementAdmin(admin.ModelAdmin):
    list_display = ("id", "text", "created_by", "created_at")
    readonly_fields = ("created_by",)

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)
        if not change:
            broadcast(
                notif_type=NotificationType.BROADCAST,
                text=obj.text,
                url=obj.url,
            )


admin.site.register(Notification, NotificationAdmin)
admin.site.register(BroadcastAnnouncement, BroadcastAnnouncementAdmin)

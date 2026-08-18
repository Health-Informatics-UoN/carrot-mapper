from django.contrib.auth.models import User

from notifications.models import Notification, NotificationType


def notify(
    *,
    recipient: User,
    notif_type: str,
    text: str,
    url: str = "",
) -> Notification:
    """Create a single Notification for one recipient."""
    if notif_type not in NotificationType.values:
        raise ValueError(f"Unknown notification type: {notif_type!r}")

    return Notification.objects.create(
        recipient=recipient,
        notif_type=notif_type,
        text=text,
        url=url,
    )


def broadcast(*, notif_type: str, text: str, url: str = "") -> int:
    """
    Fan out a Notification to every active user. Returns the number of
    notifications created.
    """
    if notif_type not in NotificationType.values:
        raise ValueError(f"Unknown notification type: {notif_type!r}")

    recipients = User.objects.filter(is_active=True)
    notifications = [
        Notification(recipient=user, notif_type=notif_type, text=text, url=url)
        for user in recipients
    ]
    created = Notification.objects.bulk_create(notifications)
    return len(created)

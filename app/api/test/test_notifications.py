from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from notifications.admin import BroadcastAnnouncementAdmin
from notifications.models import BroadcastAnnouncement, Notification, NotificationType
from rest_framework.test import APIClient
from services.notifications import broadcast, notify


class TestNotifyAndBroadcast(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(username="frodo", password="ring")
        self.inactive_user = User.objects.create(
            username="saruman", password="palantir", is_active=False
        )

    def test_notify_creates_a_notification_for_the_recipient(self):
        notification = notify(
            recipient=self.user,
            notif_type=NotificationType.SCAN_REPORT_PROCESSING_COMPLETE,
            text="Scan report 'X' finished processing",
            url="/scanreports/1",
        )

        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(
            notification.notif_type, NotificationType.SCAN_REPORT_PROCESSING_COMPLETE
        )
        self.assertIsNone(notification.read_at)

    def test_notify_rejects_unknown_type(self):
        with self.assertRaises(ValueError):
            notify(recipient=self.user, notif_type="not.a.type", text="x")

    def test_broadcast_fans_out_to_every_active_user_only(self):
        User = get_user_model()
        other_active_user = User.objects.create(username="sam", password="taters")

        created = broadcast(
            notif_type=NotificationType.BROADCAST, text="New feature!", url="/"
        )

        self.assertEqual(created, 2)
        recipients = set(
            Notification.objects.filter(
                notif_type=NotificationType.BROADCAST
            ).values_list("recipient_id", flat=True)
        )
        self.assertEqual(recipients, {self.user.id, other_active_user.id})
        self.assertFalse(
            Notification.objects.filter(recipient=self.inactive_user).exists()
        )


class TestBroadcastAnnouncementAdmin(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create(
            username="gandalf", password="youshallnotpass", is_staff=True
        )
        self.recipient = User.objects.create(username="frodo", password="ring")
        self.admin = BroadcastAnnouncementAdmin(BroadcastAnnouncement, AdminSite())
        self.factory = RequestFactory()

    def test_saving_a_new_announcement_fans_out_notifications(self):
        request = self.factory.post("/admin/notifications/broadcastannouncement/add/")
        request.user = self.admin_user
        obj = BroadcastAnnouncement(text="Carrot 2.0 is here", url="/changelog")

        self.admin.save_model(request, obj, form=None, change=False)

        obj.refresh_from_db()
        self.assertEqual(obj.created_by, self.admin_user)
        notification = Notification.objects.get(recipient=self.recipient)
        self.assertEqual(notification.notif_type, NotificationType.BROADCAST)
        self.assertEqual(notification.text, "Carrot 2.0 is here")

    def test_re_saving_an_existing_announcement_does_not_re_broadcast(self):
        obj = BroadcastAnnouncement.objects.create(
            text="Carrot 2.0 is here", url="/changelog", created_by=self.admin_user
        )
        Notification.objects.all().delete()

        request = self.factory.post(
            f"/admin/notifications/broadcastannouncement/{obj.id}/change/"
        )
        request.user = self.admin_user

        self.admin.save_model(request, obj, form=None, change=True)

        self.assertFalse(Notification.objects.exists())


class TestNotificationViews(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(username="frodo", password="ring")
        self.other_user = User.objects.create(username="sam", password="taters")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.own_notification = notify(
            recipient=self.user,
            notif_type=NotificationType.SCAN_REPORT_PROCESSING_COMPLETE,
            text="Mine",
            url="/scanreports/1",
        )
        self.other_notification = notify(
            recipient=self.other_user,
            notif_type=NotificationType.SCAN_REPORT_PROCESSING_COMPLETE,
            text="Not mine",
            url="/scanreports/2",
        )

    def test_list_only_returns_own_notifications(self):
        response = self.client.get("/api/v2/notifications/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["text"], "Mine")

    def test_list_unread_filter(self):
        self.own_notification.read_at = self.own_notification.created_at
        self.own_notification.save()

        response = self.client.get("/api/v2/notifications/?unread=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

    def test_unread_count(self):
        response = self.client.get("/api/v2/notifications/unread-count/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"count": 1})

    def test_mark_read_sets_read_at_and_is_idempotent(self):
        response = self.client.patch(
            f"/api/v2/notifications/{self.own_notification.id}/read/"
        )
        self.assertEqual(response.status_code, 200)
        self.own_notification.refresh_from_db()
        first_read_at = self.own_notification.read_at
        self.assertIsNotNone(first_read_at)

        response = self.client.patch(
            f"/api/v2/notifications/{self.own_notification.id}/read/"
        )
        self.assertEqual(response.status_code, 200)
        self.own_notification.refresh_from_db()
        self.assertEqual(self.own_notification.read_at, first_read_at)

    def test_mark_read_on_someone_elses_notification_404s(self):
        response = self.client.patch(
            f"/api/v2/notifications/{self.other_notification.id}/read/"
        )

        self.assertEqual(response.status_code, 404)
        self.other_notification.refresh_from_db()
        self.assertIsNone(self.other_notification.read_at)

    def test_mark_all_read_only_touches_own_notifications(self):
        notify(
            recipient=self.user,
            notif_type=NotificationType.AUTOMAP_COMPLETE,
            text="Also mine",
        )

        response = self.client.post("/api/v2/notifications/read-all/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"updated": 2})
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.user, read_at__isnull=True
            ).exists()
        )
        self.other_notification.refresh_from_db()
        self.assertIsNone(self.other_notification.read_at)

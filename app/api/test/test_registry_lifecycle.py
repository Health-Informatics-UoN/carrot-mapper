from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from registry.models import (
    ImportJob,
    ImportJobStatus,
    MappingSet,
    Origin,
    Status,
)
from rest_framework.test import APIClient

BASE = "/api/v2/registry/mapping-sets/"


class LifecycleTestBase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create(username="owner")
        self.other = User.objects.create(username="other")
        self.admin = User.objects.create(username="admin", is_staff=True)
        self.client = APIClient()

    def make_set(
        self,
        status=Status.DRAFT,
        version="1.0",
        job_status=ImportJobStatus.SUCCEEDED,
        **kwargs,
    ):
        job = ImportJob.objects.create(
            submitted_by=self.owner,
            origin_id=Origin.SSSOM_UPLOAD,
            status=job_status,
        )
        return MappingSet.objects.create(
            set_uri="https://x/set",
            set_version=version,
            title="A set",
            origin_id=Origin.SSSOM_UPLOAD,
            status_id=status,
            import_job=job,
            publisher=self.owner,
            **kwargs,
        )

    def post(self, mapping_set, action, user=None, **body):
        self.client.force_authenticate(user)
        return self.client.post(f"{BASE}{mapping_set.id}/{action}/", body)


class TestPublish(LifecycleTestBase):
    def test_publisher_and_admin_can_publish_a_draft(self):
        for user, version in ((self.owner, "1"), (self.admin, "2")):
            with self.subTest(user=user.username):
                mapping_set = self.make_set(version=version)
                r = self.post(mapping_set, "publish", user)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.data["status"], Status.PUBLISHED)
                self.assertIsNotNone(r.data["published_at"])
                self.assertEqual(r.data["mapping_count"], 0)

    def test_draft_is_hidden_from_other_users(self):
        mapping_set = self.make_set()
        self.assertEqual(self.post(mapping_set, "publish", self.other).status_code, 404)
        self.assertEqual(self.post(mapping_set, "publish").status_code, 401)
        mapping_set.refresh_from_db()
        self.assertEqual(mapping_set.status_id, Status.DRAFT)

    def test_only_a_draft_can_be_published(self):
        for status in (Status.PUBLISHED, Status.WITHDRAWN):
            with self.subTest(status=status):
                mapping_set = self.make_set(status=status, version=status)
                r = self.post(mapping_set, "publish", self.owner)
                self.assertEqual(r.status_code, 409)

    def test_unfinished_import_is_refused(self):
        for job_status in (
            ImportJobStatus.PENDING,
            ImportJobStatus.RUNNING,
            ImportJobStatus.FAILED,
        ):
            with self.subTest(job_status=job_status):
                mapping_set = self.make_set(version=job_status, job_status=job_status)
                r = self.post(mapping_set, "publish", self.owner)
                self.assertEqual(r.status_code, 409)
                mapping_set.refresh_from_db()
                self.assertEqual(mapping_set.status_id, Status.DRAFT)

    def test_set_whose_job_was_deleted_can_be_published(self):
        mapping_set = self.make_set()
        ImportJob.objects.filter(pk=mapping_set.import_job_id).delete()
        self.assertEqual(self.post(mapping_set, "publish", self.owner).status_code, 200)

    def test_late_published_old_version_does_not_become_latest(self):
        old = self.make_set(version="1.0")
        new = self.make_set(
            status=Status.PUBLISHED,
            version="2.0",
            published_at=timezone.now() - timedelta(days=1),
        )
        self.post(old, "publish", self.owner)
        self.client.force_authenticate(None)
        r = self.client.get(BASE, {"latest": "true"})
        self.assertEqual([row["id"] for row in r.data["results"]], [str(new.id)])


class TestWithdraw(LifecycleTestBase):
    def published(self, version="1.0"):
        return self.make_set(
            status=Status.PUBLISHED, version=version, published_at=timezone.now()
        )

    def test_publisher_can_withdraw_with_a_reason(self):
        mapping_set = self.published()
        published_at = mapping_set.published_at
        r = self.post(mapping_set, "withdraw", self.owner, reason="Wrong concepts")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["status"], Status.WITHDRAWN)
        self.assertEqual(r.data["withdrawal_reason"], "Wrong concepts")
        self.assertIsNotNone(r.data["withdrawn_at"])
        mapping_set.refresh_from_db()
        self.assertEqual(mapping_set.withdrawn_by, self.owner)
        self.assertEqual(mapping_set.published_at, published_at)

    def test_admin_can_withdraw(self):
        r = self.post(self.published(), "withdraw", self.admin, reason="Requested")
        self.assertEqual(r.status_code, 200)

    def test_other_users_are_refused(self):
        mapping_set = self.published()
        r = self.post(mapping_set, "withdraw", self.other, reason="Mine now")
        self.assertEqual(r.status_code, 403)
        r = self.post(mapping_set, "withdraw", reason="Mine now")
        self.assertEqual(r.status_code, 401)
        mapping_set.refresh_from_db()
        self.assertEqual(mapping_set.status_id, Status.PUBLISHED)

    def test_set_without_a_publisher_is_admin_only(self):
        mapping_set = self.published()
        MappingSet.objects.filter(pk=mapping_set.pk).update(publisher=None)
        r = self.post(mapping_set, "withdraw", self.other, reason="Mine now")
        self.assertEqual(r.status_code, 403)
        r = self.post(mapping_set, "withdraw", self.admin, reason="Tidying up")
        self.assertEqual(r.status_code, 200)

    def test_reason_is_required(self):
        mapping_set = self.published()
        for body in ({}, {"reason": "   "}):
            with self.subTest(body=body):
                r = self.post(mapping_set, "withdraw", self.owner, **body)
                self.assertEqual(r.status_code, 400)
                self.assertIn("reason", r.data)

    def test_only_a_published_set_can_be_withdrawn(self):
        for status in (Status.DRAFT, Status.WITHDRAWN):
            with self.subTest(status=status):
                mapping_set = self.make_set(status=status, version=status)
                r = self.post(mapping_set, "withdraw", self.owner, reason="Again")
                self.assertEqual(r.status_code, 409)

    def test_withdrawn_set_leaves_listings_but_resolves_by_id(self):
        mapping_set = self.published()
        self.post(mapping_set, "withdraw", self.owner, reason="Wrong concepts")
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(BASE).data["count"], 0)
        r = self.client.get(f"{BASE}{mapping_set.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["withdrawal_reason"], "Wrong concepts")

    def test_latest_falls_back_to_the_previous_version(self):
        old = self.published("1.0")
        new = self.published("2.0")
        self.post(new, "withdraw", self.owner, reason="Wrong concepts")
        self.client.force_authenticate(None)
        r = self.client.get(BASE, {"latest": "true"})
        self.assertEqual([row["id"] for row in r.data["results"]], [str(old.id)])

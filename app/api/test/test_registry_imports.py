from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from registry.models import (
    ImportJob,
    ImportJobStatus,
    MappingSet,
    MappingSetSeries,
    Origin,
    Status,
)
from rest_framework.test import APIClient

BASE = "/api/v2/registry/imports/"


class TestImportJobs(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create(username="owner")
        self.other = User.objects.create(username="other")
        self.admin = User.objects.create(username="admin", is_staff=True)
        self.client = APIClient()
        self.job = self.make_job(self.owner)

    @staticmethod
    def make_job(user, **kwargs):
        return ImportJob.objects.create(
            submitted_by=user, origin_id=Origin.SSSOM_UPLOAD, **kwargs
        )

    def add_set(self, job):
        series, _ = MappingSetSeries.objects.get_or_create(
            set_uri="https://x/set", defaults={"publisher": job.submitted_by}
        )
        return MappingSet.objects.create(
            series=series,
            set_version="1.0.0",
            title="A set",
            origin_id=Origin.SSSOM_UPLOAD,
            status_id=Status.DRAFT,
            import_job=job,
            publisher=job.submitted_by,
        )

    def get(self, url, user=None, **params):
        self.client.force_authenticate(user)
        return self.client.get(url, params)

    def test_anonymous_is_rejected(self):
        self.assertEqual(self.get(BASE).status_code, 401)
        self.assertEqual(self.get(f"{BASE}{self.job.id}/").status_code, 401)

    def test_list_only_shows_the_callers_jobs(self):
        self.make_job(self.other)
        for user, expected in ((self.owner, 1), (self.admin, 0)):
            with self.subTest(user=user.username):
                r = self.get(BASE, user)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.data["count"], expected)

    def test_list_is_newest_first_including_jobs_not_started(self):
        older = self.make_job(self.owner, started_at=timezone.now())
        ImportJob.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )
        r = self.get(BASE, self.owner)
        self.assertEqual(
            [row["id"] for row in r.data["results"]],
            [str(self.job.id), str(older.id)],
        )

    def test_list_filters_by_status(self):
        failed = self.make_job(self.owner, status=ImportJobStatus.FAILED)
        r = self.get(BASE, self.owner, status="FAILED,SUCCEEDED")
        self.assertEqual([row["id"] for row in r.data["results"]], [str(failed.id)])

    def test_detail_is_for_the_submitter_and_admins(self):
        url = f"{BASE}{self.job.id}/"
        for user, expected in ((self.owner, 200), (self.admin, 200), (self.other, 404)):
            with self.subTest(user=user.username):
                self.assertEqual(self.get(url, user).status_code, expected)

    def test_detail_reports_progress_without_internals(self):
        issues = [{"level": "error", "code": "unknown_predicate", "message": "x"}]
        job = self.make_job(
            self.owner,
            status=ImportJobStatus.FAILED,
            validation_issues=issues,
            error_message="SSSOM file failed validation",
            file_key="imports/secret/original.sssom.tsv",
            dag_run_id="manual__1",
            params={"user_id": self.owner.id},
        )
        data = self.get(f"{BASE}{job.id}/", self.owner).data
        self.assertEqual(data["status"], ImportJobStatus.FAILED)
        self.assertEqual(data["origin"], Origin.SSSOM_UPLOAD)
        self.assertEqual(data["validation_issues"], issues)
        self.assertEqual(data["error_message"], "SSSOM file failed validation")
        self.assertIsNotNone(data["created_at"])
        for internal in ("file_key", "dag_run_id", "params", "submitted_by"):
            self.assertNotIn(internal, data)

    def test_mapping_set_appears_once_the_job_has_succeeded(self):
        mapping_set = self.add_set(self.job)
        url = f"{BASE}{self.job.id}/"
        self.job.status = ImportJobStatus.RUNNING
        self.job.save(update_fields=["status"])
        self.assertIsNone(self.get(url, self.owner).data["mapping_set"])

        self.job.status = ImportJobStatus.SUCCEEDED
        self.job.save(update_fields=["status"])
        self.assertEqual(
            self.get(url, self.owner).data["mapping_set"]["id"], str(mapping_set.id)
        )

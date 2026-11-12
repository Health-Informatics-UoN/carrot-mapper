from unittest.mock import patch

from activity_log.models import ActivityLog, Verb
from data.models import Concept
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from mapping.models import (
    DataPartner,
    Dataset,
    MappingRule,
    OmopField,
    OmopTable,
    Project,
    ScanReport,
    ScanReportConcept,
    ScanReportField,
    ScanReportTable,
)
from registry.models import (
    ImportJob,
    ImportJobStatus,
    MappingSet,
    Origin,
    Status,
)
from registry.services import scan_report_set_uri
from rest_framework.test import APIClient

TRIGGER = "registry.services.worker_service.trigger_registry_import"


class TestScanReportRegistryPublish(TestCase):
    def setUp(self):
        User = get_user_model()
        self.author = User.objects.create(username="frodo_baggins")
        self.viewer = User.objects.create(username="sam_gamgee")

        dataset = Dataset.objects.create(
            name="Dataset",
            visibility="PUBLIC",
            data_partner=DataPartner.objects.create(name="Data Partner"),
        )
        project = Project.objects.create(name="Project")
        project.members.add(self.author, self.viewer)
        project.datasets.add(dataset)

        self.scan_report = ScanReport.objects.create(
            author=self.author,
            name="Scan Report",
            dataset="Dataset Name",
            parent_dataset=dataset,
            visibility="PUBLIC",
        )
        self.table = ScanReportTable.objects.create(
            scan_report=self.scan_report, name="Table"
        )
        self.field = ScanReportField.objects.create(
            scan_report_table=self.table,
            name="gender",
            description_column="",
            type_column="VARCHAR",
        )
        self.person = OmopTable.objects.create(table="person")
        self.concept = Concept.objects.create(
            concept_id=910001,
            concept_name="Male",
            concept_code="Male",
            domain_id="Gender",
            vocabulary_id="Test",
            concept_class_id="Test",
            standard_concept="S",
            valid_start_date="2020-01-01",
            valid_end_date="2099-12-31",
        )
        self.sr_concept = ScanReportConcept.objects.create(
            concept=self.concept,
            content_type=ContentType.objects.get(
                app_label="mapping", model="scanreportfield"
            ),
            object_id=self.field.id,
            creation_type="M",
        )

        self.client = APIClient()
        self.client.force_authenticate(self.author)
        self.url = (
            f"/api/v2/registry/scanreports/{self.scan_report.id}/registry-publish/"
        )
        self.body = {
            "title": "Gender mappings",
            "include_orcid_ids": True,
            "set_version": "1.0",
            "license": "CC-BY-4.0",
            "description": "Mappings from the test scan report.",
        }

    def _add_rule(self, omop_field_name="gender_concept_id"):
        MappingRule.objects.create(
            scan_report=self.scan_report,
            omop_field=OmopField.objects.create(
                table=self.person, field=omop_field_name
            ),
            source_field=self.field,
            concept=self.sr_concept,
        )

    @patch(TRIGGER, return_value="manual__run-1")
    def test_publish_creates_job_and_triggers_dag(self, mock_trigger):
        self._add_rule()

        response = self.client.post(self.url, self.body, format="json")

        self.assertEqual(response.status_code, 202)
        job = ImportJob.objects.get(pk=response.data["import_job_id"])
        self.assertEqual(response.data["status"], ImportJobStatus.PENDING)
        self.assertEqual(job.origin_id, Origin.CARROT_DIRECT_PUBLISH)
        self.assertEqual(job.submitted_by, self.author)
        self.assertEqual(job.dag_run_id, "manual__run-1")

        conf = mock_trigger.call_args.args[0]
        self.assertEqual(conf["import_job_id"], str(job.id))
        self.assertEqual(conf["origin"], Origin.CARROT_DIRECT_PUBLISH)
        self.assertEqual(conf["scan_report_id"], self.scan_report.id)
        self.assertEqual(conf["user_id"], self.author.id)
        self.assertEqual(
            conf["overrides"],
            {
                "set_uri": scan_report_set_uri(self.scan_report),
                "set_version": "1.0",
                "title": "Gender mappings",
                "include_orcid_ids": True,
                "description": "Mappings from the test scan report.",
                "license": "CC-BY-4.0",
                "status": Status.PUBLISHED,
            },
        )
        self.assertTrue(
            ActivityLog.objects.filter(
                scope_id=self.scan_report.id, verb=Verb.REGISTRY_PUBLISH_REQUESTED
            ).exists()
        )

    @patch(TRIGGER)
    def test_viewer_cannot_publish(self, mock_trigger):
        self._add_rule()
        self.client.force_authenticate(self.viewer)

        response = self.client.post(self.url, self.body, format="json")

        self.assertEqual(response.status_code, 403)
        mock_trigger.assert_not_called()

    @patch(TRIGGER)
    def test_rejected_without_concept_mappings(self, mock_trigger):
        # Rules to non-concept fields produce no SSSOM rows.
        self._add_rule(omop_field_name="person_id")

        response = self.client.post(self.url, self.body, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ImportJob.objects.exists())
        mock_trigger.assert_not_called()

    @patch(TRIGGER)
    def test_rejected_with_unknown_license(self, mock_trigger):
        self._add_rule()

        response = self.client.post(
            self.url, {**self.body, "license": "NOT-A-LICENSE"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("license", response.data)
        mock_trigger.assert_not_called()

    @patch(TRIGGER)
    def test_conflict_when_version_already_exists(self, mock_trigger):
        self._add_rule()
        MappingSet.objects.create(
            set_uri=scan_report_set_uri(self.scan_report),
            set_version="1.0",
            title="Existing",
            origin_id=Origin.CARROT_DIRECT_PUBLISH,
        )

        response = self.client.post(self.url, self.body, format="json")

        self.assertEqual(response.status_code, 409)
        mock_trigger.assert_not_called()

    @patch(TRIGGER, return_value="run")
    def test_identical_in_flight_publish_returns_existing_job(self, mock_trigger):
        self._add_rule()

        first = self.client.post(self.url, self.body, format="json")
        second = self.client.post(self.url, self.body, format="json")

        self.assertEqual(second.status_code, 202)
        self.assertEqual(second.data["import_job_id"], first.data["import_job_id"])
        self.assertEqual(ImportJob.objects.count(), 1)
        mock_trigger.assert_called_once()

    @patch(TRIGGER, return_value="run")
    def test_different_in_flight_publish_of_same_version_conflicts(self, mock_trigger):
        self._add_rule()

        first = self.client.post(self.url, self.body, format="json")
        second = self.client.post(
            self.url, {**self.body, "title": "Another title"}, format="json"
        )

        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.data["import_job_id"], str(first.data["import_job_id"]))
        mock_trigger.assert_called_once()

    @patch(TRIGGER, side_effect=RuntimeError("airflow down"))
    def test_trigger_failure_marks_job_failed(self, mock_trigger):
        self._add_rule()

        response = self.client.post(self.url, self.body, format="json")

        self.assertEqual(response.status_code, 503)
        job = ImportJob.objects.get()
        self.assertEqual(job.status, ImportJobStatus.FAILED)
        self.assertIn("airflow down", job.error_message)
        self.assertIsNotNone(job.finished_at)

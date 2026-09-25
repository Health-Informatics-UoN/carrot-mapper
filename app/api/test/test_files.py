from unittest.mock import patch

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
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


class TestFileDownloadViewPersonValidation(TestCase):
    """
    Rule downloads must fail before any worker is triggered if the scan
    report has no mapping to the OMOP Person table, since the Person table
    is mandatory in the OMOP CDM.
    """

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(username="frodo", password="baggins")
        Token.objects.create(user=self.user)

        self.data_partner = DataPartner.objects.create(name="Data Partner")
        self.dataset = Dataset.objects.create(
            name="Dataset", visibility="PUBLIC", data_partner=self.data_partner
        )
        self.project = Project.objects.create(name="Project")
        self.project.members.add(self.user)
        self.project.datasets.add(self.dataset)

        self.scan_report = ScanReport.objects.create(
            author=self.user,
            name="Scan Report",
            dataset="Dataset Name",
            parent_dataset=self.dataset,
        )
        self.scan_report.viewers.add(self.user)

        self.scan_report_table = ScanReportTable.objects.create(
            scan_report=self.scan_report, name="Table"
        )
        self.gender_field = ScanReportField.objects.create(
            scan_report_table=self.scan_report_table,
            name="gender",
            description_column="",
            type_column="VARCHAR",
        )

        self.person_table = OmopTable.objects.create(table="person")
        self.person_field = OmopField.objects.create(
            table=self.person_table, field="gender_concept_id"
        )

        self.content_type = ContentType.objects.get(
            app_label="mapping", model="scanreportfield"
        )
        self.gender_concept = Concept.objects.create(
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

        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _post_download_request(self):
        return self.client.post(
            f"/api/v2/scanreports/{self.scan_report.id}/rules/downloads/",
            {"scan_report_id": self.scan_report.id, "file_type": "application/json_v1"},
        )

    @patch("files.views.worker_service.trigger_rules_export")
    def test_download_rejected_when_no_person_mapping_exists(self, mock_trigger):
        response = self._post_download_request()

        self.assertEqual(response.status_code, 400)
        mock_trigger.assert_not_called()

    @patch("files.views.worker_service.trigger_rules_export")
    def test_download_accepted_when_person_mapping_exists(self, mock_trigger):
        scan_report_concept = ScanReportConcept.objects.create(
            concept=self.gender_concept,
            content_type=self.content_type,
            object_id=self.gender_field.id,
            creation_type="M",
        )
        MappingRule.objects.create(
            scan_report=self.scan_report,
            omop_field=self.person_field,
            source_field=self.gender_field,
            concept=scan_report_concept,
        )

        response = self._post_download_request()

        self.assertEqual(response.status_code, 202)
        mock_trigger.assert_called_once()

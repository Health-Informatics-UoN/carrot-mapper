from unittest import mock

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from mapping.models import (
    Concept,
    DataPartner,
    Dataset,
    MappingRecommendation,
    MappingRule,
    OmopField,
    OmopTable,
    Project,
    ScanReport,
    ScanReportConcept,
    ScanReportField,
    ScanReportTable,
    ScanReportValue,
    VisibilityChoices,
)
from rest_framework.test import APIClient
from services.storage_service import StorageService


def _azure_storage_service(blob_client: mock.Mock) -> StorageService:
    service = StorageService.__new__(StorageService)
    service._s3_client = None
    service._azure_client = mock.Mock()
    service._azure_client.get_container_client.return_value.get_blob_client.return_value = blob_client
    return service


class TestAzureDeleteFile(TestCase):
    def test_deletes_blob_and_snapshots(self):
        blob_client = mock.Mock()
        service = _azure_storage_service(blob_client)

        self.assertTrue(service.delete_file("sr.xlsx", "scan-reports"))
        blob_client.delete_blob.assert_called_once_with(delete_snapshots="include")

    def test_missing_blob_is_treated_as_deleted(self):
        blob_client = mock.Mock()
        blob_client.delete_blob.side_effect = ResourceNotFoundError("BlobNotFound")
        service = _azure_storage_service(blob_client)

        self.assertFalse(service.delete_file("sr.xlsx", "scan-reports"))

    def test_other_errors_still_raise(self):
        blob_client = mock.Mock()
        blob_client.delete_blob.side_effect = HttpResponseError("Forbidden")
        service = _azure_storage_service(blob_client)

        with self.assertRaises(ValueError):
            service.delete_file("sr.xlsx", "scan-reports")


@mock.patch("api.views.storage_service")
class TestScanReportDelete(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="frodo")
        dataset = Dataset.objects.create(
            name="The Shire",
            visibility=VisibilityChoices.PUBLIC,
            data_partner=DataPartner.objects.create(name="Hobbits"),
        )
        project = Project.objects.create(name="Fellowship")
        project.members.add(self.user)
        project.datasets.add(dataset)

        self.scan_report = ScanReport.objects.create(
            author=self.user,
            name="sr_20261109-120000_abcd1234.xlsx",
            dataset="Second Breakfast",
            visibility=VisibilityChoices.PUBLIC,
            parent_dataset=dataset,
        )
        table = ScanReportTable.objects.create(
            scan_report=self.scan_report, name="person"
        )
        field = ScanReportField.objects.create(
            scan_report_table=table,
            name="gender",
            description_column="",
            type_column="VARCHAR",
        )
        value = ScanReportValue.objects.create(
            scan_report_field=field, value="M", frequency=10
        )
        concept = Concept.objects.create(
            concept_id=8507,
            concept_name="Male",
            concept_code="M",
            domain_id="Gender",
            vocabulary_id="Gender",
            concept_class_id="Gender",
            standard_concept="S",
            valid_start_date="2020-01-01",
            valid_end_date="2099-12-31",
        )
        value_ct = ContentType.objects.get_for_model(ScanReportValue)
        field_ct = ContentType.objects.get_for_model(ScanReportField)
        value_concept = ScanReportConcept.objects.create(
            concept=concept, content_type=value_ct, object_id=value.id
        )
        ScanReportConcept.objects.create(
            concept=concept, content_type=field_ct, object_id=field.id
        )
        MappingRecommendation.objects.create(
            concept=concept, content_type=value_ct, object_id=value.id
        )
        MappingRule.objects.create(
            scan_report=self.scan_report,
            omop_field=OmopField.objects.create(
                table=OmopTable.objects.create(table="person"),
                field="gender_concept_id",
            ),
            source_field=field,
            concept=value_concept,
        )

        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _delete(self):
        return self.client.delete(f"/api/v2/scanreports/{self.scan_report.id}/")

    def test_deletes_rows_then_file(self, storage):
        response = self._delete()

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ScanReport.objects.exists())
        for model in (
            ScanReportTable,
            ScanReportField,
            ScanReportValue,
            ScanReportConcept,
            MappingRecommendation,
            MappingRule,
        ):
            self.assertFalse(model.objects.exists(), model.__name__)
        storage.delete_file.assert_called_once_with(
            self.scan_report.name, "scan-reports"
        )

    def test_failed_db_delete_keeps_the_file(self, storage):
        with mock.patch.object(ScanReport, "delete", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                self._delete()

        # Everything rolls back and the file is untouched, so a retry works.
        self.assertTrue(ScanReport.objects.exists())
        self.assertTrue(ScanReportValue.objects.exists())
        self.assertTrue(ScanReportConcept.objects.exists())
        storage.delete_file.assert_not_called()

    def test_file_delete_failure_does_not_fail_the_request(self, storage):
        storage.delete_file.side_effect = ValueError("boom")

        response = self._delete()

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ScanReport.objects.exists())

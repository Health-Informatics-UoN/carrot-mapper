from io import BytesIO
from unittest import mock

from activity_log.models import ActivityLog, ScopeType, Verb
from data.models import Concept
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from files.models import FileDownload, FileType
from mapping.models import (
    DataPartner,
    Dataset,
    MappingStatus,
    OmopField,
    OmopTable,
    Project,
    ScanReport,
    ScanReportConcept,
    ScanReportField,
    ScanReportTable,
    VisibilityChoices,
)
from openpyxl import Workbook
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from services.activity_log import record


class TestRecordActivityLog(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(username="frodo", password="ring")

    def test_record_creates_row_with_actor_label_snapshot(self):
        log = record(
            scope_type=ScopeType.SCAN_REPORT,
            scope_id=1,
            verb=Verb.MAPPING_ADDED,
            actor=self.user,
            object_type="scanreportfield",
            object_id=2,
            detail={
                "concept_id": 12345,
                "concept_name": "Test Concept",
                "table_name": "Test Table",
                "field_name": "Test Field",
            },
        )

        self.assertEqual(log.actor, self.user)
        self.assertEqual(log.actor_label, "frodo")
        self.assertEqual(
            log.detail,
            {
                "concept_id": 12345,
                "concept_name": "Test Concept",
                "table_name": "Test Table",
                "field_name": "Test Field",
            },
        )

    def test_record_with_no_actor(self):
        log = record(
            scope_type=ScopeType.SCAN_REPORT,
            scope_id=1,
            verb=Verb.RULES_DOWNLOADED,
            actor=None,
            detail={"file_type": "CSV", "file_name": "rules.csv"},
        )

        self.assertIsNone(log.actor)
        self.assertEqual(log.actor_label, "")

    def test_record_rejects_unknown_verb(self):
        with self.assertRaises(ValueError):
            record(
                scope_type=ScopeType.SCAN_REPORT,
                scope_id=1,
                verb="not.a.verb",
                actor=self.user,
            )

    def test_record_rejects_unknown_scope_type(self):
        with self.assertRaises(ValueError):
            record(
                scope_type="not-a-scope",
                scope_id=1,
                verb=Verb.MAPPING_ADDED,
                actor=self.user,
                detail={"concept_id": 1, "concept_name": "x"},
            )

    def test_record_rejects_detail_missing_required_keys(self):
        with self.assertRaises(TypeError):
            record(
                scope_type=ScopeType.SCAN_REPORT,
                scope_id=1,
                verb=Verb.MAPPING_ADDED,
                actor=self.user,
                detail={"concept_id": 1},
            )

    def test_record_rejects_detail_on_verb_that_accepts_none(self):
        # AUTOMAP_RAN has a schema, so an unrelated verb with no schema
        # (there are none currently) would reject a detail payload. Use a
        # verb with a schema but the wrong keys to prove validation runs.
        with self.assertRaises(TypeError):
            record(
                scope_type=ScopeType.SCAN_REPORT,
                scope_id=1,
                verb=Verb.RULES_DOWNLOADED,
                actor=self.user,
                detail={"unexpected_key": "x"},
            )


class ActivityLogEmitSiteTestBase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(username="sam", password="taters")
        Token.objects.create(user=self.user)

        self.data_partner = DataPartner.objects.create(name="The Shire")
        self.dataset = Dataset.objects.create(
            name="Fellowship Dataset",
            visibility=VisibilityChoices.PUBLIC,
            data_partner=self.data_partner,
        )
        self.project = Project.objects.create(name="The Fellowship")
        self.project.members.add(self.user)
        self.project.datasets.add(self.dataset)

        self.scan_report = ScanReport.objects.create(
            author=self.user,
            name="Scan Report",
            dataset="Dataset Name",
            visibility=VisibilityChoices.PUBLIC,
            parent_dataset=self.dataset,
        )
        self.scan_report.editors.add(self.user)

        self.table = ScanReportTable.objects.create(
            scan_report=self.scan_report, name="Condition Occurrence"
        )
        self.person_id_field = ScanReportField.objects.create(
            scan_report_table=self.table,
            name="person_id",
            description_column="",
            type_column="INT",
        )
        self.date_field = ScanReportField.objects.create(
            scan_report_table=self.table,
            name="date",
            description_column="",
            type_column="VARCHAR",
        )
        self.condition_field = ScanReportField.objects.create(
            scan_report_table=self.table,
            name="condition",
            description_column="",
            type_column="VARCHAR",
        )
        self.table.person_id = self.person_id_field
        self.table.date_event = self.date_field
        self.table.save()

        self.concept = Concept.objects.create(
            concept_id=98765,
            concept_name="Test Condition",
            concept_code="TEST-COND",
            domain_id="Condition",
            vocabulary_id="Test",
            concept_class_id="Test",
            standard_concept="S",
            valid_start_date="2020-01-01",
            valid_end_date="2099-12-31",
        )

        # Minimal condition_occurrence OMOP fields needed by save_mapping_rules().
        condition_table = OmopTable.objects.create(table="condition_occurrence")
        for field_name in [
            "person_id",
            "condition_start_datetime",
            "condition_end_datetime",
            "condition_source_concept_id",
            "condition_concept_id",
            "condition_source_value",
        ]:
            OmopField.objects.create(table=condition_table, field=field_name)

        self.client = APIClient()
        self.client.force_authenticate(self.user)


class TestScanReportUploadedEmitsActivityLog(ActivityLogEmitSiteTestBase):
    def setUp(self):
        super().setUp()
        self.dataset.admins.add(self.user)

    def _build_scan_report_file(self) -> SimpleUploadedFile:
        wb = Workbook()
        ws = wb.active
        ws.title = "Field Overview"
        ws.append(
            [
                "Table",
                "Field",
                "Description",
                "Type",
                "Max length",
                "N rows",
                "N rows checked",
                "Fraction empty",
                "N unique values",
                "Fraction unique",
            ]
        )
        ws.append(["Table1", "Field1", "", "VARCHAR", 10, -1, 0, 0.0, 0, 0.0])

        table_sheet = wb.create_sheet("Table1")
        table_sheet.append(["Field1", "Frequency"])

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return SimpleUploadedFile(
            "new_scan_report.xlsx",
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @mock.patch("api.views.worker_service.trigger_scan_report_processing")
    @mock.patch("api.views.storage_service.upload_file")
    def test_uploading_a_scan_report_records_scan_report_uploaded(
        self, mock_upload_file, mock_trigger_processing
    ):
        response = self.client.post(
            "/api/v2/scanreports/",
            {
                "scan_report_file": self._build_scan_report_file(),
                "dataset": "New Scan Report",
                "parent_dataset": self.dataset.id,
                "visibility": "PUBLIC",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.content)
        mock_trigger_processing.assert_called_once()

        new_scan_report = ScanReport.objects.get(dataset="New Scan Report")
        log = ActivityLog.objects.get(verb=Verb.SCAN_REPORT_UPLOADED)
        self.assertEqual(log.scope_type, ScopeType.SCAN_REPORT)
        self.assertEqual(log.scope_id, new_scan_report.id)
        self.assertEqual(log.actor, self.user)
        self.assertEqual(log.object_type, "scanreport")
        self.assertEqual(log.object_id, new_scan_report.id)
        self.assertEqual(
            log.detail,
            {
                "scan_report_name": "New Scan Report",
                "file_name": new_scan_report.name,
            },
        )


class TestMappingAddedEmitsActivityLog(ActivityLogEmitSiteTestBase):
    def test_adding_a_concept_records_mapping_added(self):
        response = self.client.post(
            "/api/v2/scanreports/concepts/",
            {
                "object_id": self.condition_field.id,
                "concept": self.concept.concept_id,
                "content_type": "scanreportfield",
                "table_id": self.table.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)

        log = ActivityLog.objects.get(verb=Verb.MAPPING_ADDED)
        self.assertEqual(log.scope_type, ScopeType.SCAN_REPORT)
        self.assertEqual(log.scope_id, self.scan_report.id)
        self.assertEqual(log.actor, self.user)
        self.assertEqual(log.object_type, "scanreportfield")
        self.assertEqual(log.object_id, self.condition_field.id)
        self.assertEqual(
            log.detail,
            {
                "concept_id": self.concept.concept_id,
                "concept_name": "Test Condition",
                "table_name": "Condition Occurrence",
                "field_name": "condition",
            },
        )


class TestMappingDeletedEmitsActivityLog(ActivityLogEmitSiteTestBase):
    def setUp(self):
        super().setUp()
        content_type = ContentType.objects.get(
            app_label="mapping", model="scanreportfield"
        )
        self.scan_report_concept = ScanReportConcept.objects.create(
            concept=self.concept,
            content_type=content_type,
            object_id=self.condition_field.id,
        )

    def test_deleting_a_concept_records_mapping_deleted(self):
        response = self.client.delete(
            f"/api/v2/scanreports/concepts/{self.scan_report_concept.id}/"
        )

        self.assertEqual(response.status_code, 204, response.content)

        log = ActivityLog.objects.get(verb=Verb.MAPPING_DELETED)
        self.assertEqual(log.scope_type, ScopeType.SCAN_REPORT)
        self.assertEqual(log.scope_id, self.scan_report.id)
        self.assertEqual(log.actor, self.user)
        self.assertEqual(log.object_type, "scanreportfield")
        self.assertEqual(log.object_id, self.condition_field.id)
        self.assertEqual(
            log.detail,
            {
                "concept_id": self.concept.concept_id,
                "concept_name": "Test Condition",
                "table_name": "Condition Occurrence",
                "field_name": "condition",
            },
        )


class TestAutomapRanEmitsActivityLog(ActivityLogEmitSiteTestBase):
    @mock.patch("api.views.worker_service.trigger_auto_mapping")
    def test_patching_a_table_records_automap_ran(self, mock_trigger):
        response = self.client.patch(
            f"/api/v2/scanreports/{self.scan_report.id}/tables/{self.table.id}/",
            {"trigger_reuse": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        mock_trigger.assert_called_once()

        log = ActivityLog.objects.get(verb=Verb.AUTOMAP_RAN)
        self.assertEqual(log.scope_type, ScopeType.SCAN_REPORT)
        self.assertEqual(log.scope_id, self.scan_report.id)
        self.assertEqual(log.actor, self.user)
        self.assertEqual(
            log.detail,
            {
                "table_id": self.table.id,
                "table_name": self.table.name,
                "trigger_reuse_concepts": True,
            },
        )


class TestRulesDownloadedEmitsActivityLog(ActivityLogEmitSiteTestBase):
    def setUp(self):
        super().setUp()
        self.file_type = FileType.objects.create(value="text/csv", display_name="CSV")
        self.file_download = FileDownload.objects.create(
            name="rules.csv",
            scan_report=self.scan_report,
            user=self.user,
            file_type=self.file_type,
            file_url="rules.csv",
        )

    @mock.patch("files.views.storage_service.get_file", return_value=b"data")
    def test_downloading_a_file_records_rules_downloaded(self, mock_get_file):
        response = self.client.get(
            f"/api/v2/scanreports/{self.scan_report.id}/rules/downloads/{self.file_download.id}/"
        )

        self.assertEqual(response.status_code, 200, response.content)

        log = ActivityLog.objects.get(verb=Verb.RULES_DOWNLOADED)
        self.assertEqual(log.scope_type, ScopeType.SCAN_REPORT)
        self.assertEqual(log.scope_id, self.scan_report.id)
        self.assertEqual(log.actor, self.user)
        self.assertEqual(log.object_type, "filedownload")
        self.assertEqual(log.object_id, self.file_download.id)
        self.assertEqual(log.detail, {"file_type": "CSV", "file_name": "rules.csv"})


class TestRulesExportRequestedEmitsActivityLog(ActivityLogEmitSiteTestBase):
    @mock.patch("files.views.worker_service.trigger_rules_export")
    def test_requesting_an_export_records_rules_export_requested(
        self, mock_trigger_export
    ):
        response = self.client.post(
            f"/api/v2/scanreports/{self.scan_report.id}/rules/downloads/",
            {"scan_report_id": self.scan_report.id, "file_type": "text/csv"},
            format="json",
        )

        self.assertEqual(response.status_code, 202, response.content)
        mock_trigger_export.assert_called_once()

        log = ActivityLog.objects.get(verb=Verb.RULES_EXPORT_REQUESTED)
        self.assertEqual(log.scope_type, ScopeType.SCAN_REPORT)
        self.assertEqual(log.scope_id, self.scan_report.id)
        self.assertEqual(log.actor, self.user)
        self.assertEqual(log.object_type, "scanreport")
        self.assertEqual(log.object_id, self.scan_report.id)
        self.assertEqual(log.detail, {"file_type": "CSV"})


class TestScanReportUpdatedEmitsActivityLog(ActivityLogEmitSiteTestBase):
    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.new_editor = User.objects.create(username="pippin", password="shire")
        self.project.members.add(self.new_editor)

    def test_renaming_and_changing_editors_records_scan_report_updated(self):
        response = self.client.patch(
            f"/api/v2/scanreports/{self.scan_report.id}/",
            {
                "dataset": "Renamed Scan Report",
                "visibility": "RESTRICTED",
                "editors": [self.new_editor.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)

        log = ActivityLog.objects.get(verb=Verb.SCAN_REPORT_UPDATED)
        self.assertEqual(log.scope_type, ScopeType.SCAN_REPORT)
        self.assertEqual(log.scope_id, self.scan_report.id)
        self.assertEqual(log.actor, self.user)
        self.assertEqual(
            log.detail,
            {
                "name_from": "Dataset Name",
                "name_to": "Renamed Scan Report",
                "visibility_from": "PUBLIC",
                "visibility_to": "RESTRICTED",
                "author_from": None,
                "author_to": None,
                "mapping_status_from": None,
                "mapping_status_to": None,
                "viewers_added": [],
                "viewers_removed": [],
                "editors_added": ["pippin"],
                "editors_removed": ["sam"],
            },
        )

    def test_changing_mapping_status_records_scan_report_updated(self):
        self.scan_report.mapping_status = MappingStatus.objects.get(value="PENDING")
        self.scan_report.save()

        response = self.client.patch(
            f"/api/v2/scanreports/{self.scan_report.id}/",
            {"mapping_status": {"value": "COMPLETE"}},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)

        log = ActivityLog.objects.get(verb=Verb.SCAN_REPORT_UPDATED)
        self.assertEqual(log.scope_type, ScopeType.SCAN_REPORT)
        self.assertEqual(log.scope_id, self.scan_report.id)
        self.assertEqual(log.actor, self.user)
        self.assertEqual(
            log.detail,
            {
                "name_from": None,
                "name_to": None,
                "visibility_from": None,
                "visibility_to": None,
                "author_from": None,
                "author_to": None,
                "mapping_status_from": "PENDING",
                "mapping_status_to": "COMPLETE",
                "viewers_added": [],
                "viewers_removed": [],
                "editors_added": [],
                "editors_removed": [],
            },
        )

    def test_updating_unrelated_field_does_not_record_an_event(self):
        response = self.client.patch(
            f"/api/v2/scanreports/{self.scan_report.id}/",
            {"hidden": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(
            ActivityLog.objects.filter(verb=Verb.SCAN_REPORT_UPDATED).exists()
        )


class TestDatasetUpdatedEmitsActivityLog(ActivityLogEmitSiteTestBase):
    def setUp(self):
        super().setUp()
        self.dataset.admins.add(self.user)
        User = get_user_model()
        self.new_viewer = User.objects.create(username="merry", password="shire")

    def test_renaming_and_changing_viewers_records_dataset_updated(self):
        response = self.client.patch(
            f"/api/v2/datasets/{self.dataset.id}/",
            data={
                "name": "Renamed Dataset",
                "viewers": [self.new_viewer.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)

        log = ActivityLog.objects.get(verb=Verb.DATASET_UPDATED)
        self.assertEqual(log.scope_type, ScopeType.DATASET)
        self.assertEqual(log.scope_id, self.dataset.id)
        self.assertEqual(log.actor, self.user)
        self.assertEqual(
            log.detail,
            {
                "name_from": "Fellowship Dataset",
                "name_to": "Renamed Dataset",
                "visibility_from": None,
                "visibility_to": None,
                "admins_added": [],
                "admins_removed": [],
                "viewers_added": ["merry"],
                "viewers_removed": [],
                "editors_added": [],
                "editors_removed": [],
            },
        )

    def test_updating_unrelated_field_does_not_record_an_event(self):
        response = self.client.patch(
            f"/api/v2/datasets/{self.dataset.id}/",
            data={"hidden": True},
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(ActivityLog.objects.filter(verb=Verb.DATASET_UPDATED).exists())


class TestScanReportActivityLogView(ActivityLogEmitSiteTestBase):
    def setUp(self):
        super().setUp()
        record(
            scope_type=ScopeType.SCAN_REPORT,
            scope_id=self.scan_report.id,
            verb=Verb.AUTOMAP_RAN,
            actor=self.user,
            object_type="scanreporttable",
            object_id=self.table.id,
            detail={
                "table_id": self.table.id,
                "table_name": self.table.name,
                "trigger_reuse_concepts": True,
            },
        )

    def test_viewer_can_list_scan_report_logs(self):
        response = self.client.get(f"/api/v2/scanreports/{self.scan_report.id}/logs/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(
            data["results"][0]["scan_report_name"], self.scan_report.dataset
        )

    def test_non_member_forbidden(self):
        User = get_user_model()
        outsider = User.objects.create(username="gollum", password="precious")
        self.client.force_authenticate(outsider)

        response = self.client.get(f"/api/v2/scanreports/{self.scan_report.id}/logs/")

        self.assertEqual(response.status_code, 403)


class TestDatasetActivityLogView(ActivityLogEmitSiteTestBase):
    def setUp(self):
        super().setUp()
        record(
            scope_type=ScopeType.SCAN_REPORT,
            scope_id=self.scan_report.id,
            verb=Verb.AUTOMAP_RAN,
            actor=self.user,
            object_type="scanreporttable",
            object_id=self.table.id,
            detail={
                "table_id": self.table.id,
                "table_name": self.table.name,
                "trigger_reuse_concepts": True,
            },
        )

    def test_viewer_can_list_dataset_logs_rolled_up_from_scan_reports(self):
        response = self.client.get(f"/api/v2/datasets/{self.dataset.id}/logs/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(
            data["results"][0]["scan_report_name"], self.scan_report.dataset
        )

    def test_non_member_forbidden(self):
        User = get_user_model()
        outsider = User.objects.create(username="gollum", password="precious")
        self.client.force_authenticate(outsider)

        response = self.client.get(f"/api/v2/datasets/{self.dataset.id}/logs/")

        self.assertEqual(response.status_code, 403)

"""
Table roles: death tables now being identified by role, the deprecated
death_table API flag, and the role's database default.

Uses setUpTestData for OmopTable/OmopField rows and clears the
_get_omop_field cache around the class, for the reasons given on
test_views.TestPersonConceptValidation.
"""

from api.serializers import (
    ScanReportTableEditSerializer,
    ScanReportTableListSerializerV2,
)
from data.models import Concept
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from mapping.models import (
    DataPartner,
    Dataset,
    OmopField,
    OmopTable,
    Project,
    ScanReport,
    ScanReportConcept,
    ScanReportField,
    ScanReportTable,
    TableRole,
    VisibilityChoices,
)
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from services.rules import _get_omop_field, save_mapping_rules

OMOP_TABLES = {
    "condition_occurrence": [
        "person_id",
        "condition_start_datetime",
        "condition_end_datetime",
        "condition_concept_id",
        "condition_source_concept_id",
        "condition_source_value",
        "condition_type_concept_id",
    ],
    "death": [
        "person_id",
        "death_datetime",
        "cause_concept_id",
        "cause_source_concept_id",
        "cause_source_value",
    ],
}


def _field(table, name, type_column="VARCHAR"):
    return ScanReportField.objects.create(
        scan_report_table=table,
        name=name,
        description_column="",
        type_column=type_column,
    )


def _concept(concept_id, name, domain_id):
    return Concept.objects.create(
        concept_id=concept_id,
        concept_name=name,
        concept_code=str(concept_id),
        domain_id=domain_id,
        vocabulary_id="SNOMED",
        concept_class_id="Test",
        standard_concept="S",
        valid_start_date="2020-01-01",
        valid_end_date="2099-12-31",
    )


class NoteTablesTestBase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _get_omop_field.cache_clear()

    @classmethod
    def tearDownClass(cls):
        _get_omop_field.cache_clear()
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create(username="merry", password="x")
        Token.objects.create(user=cls.user)
        partner = DataPartner.objects.create(name="Bree")
        dataset = Dataset.objects.create(
            name="Notes", visibility=VisibilityChoices.PUBLIC, data_partner=partner
        )
        cls.project = Project.objects.create(name="Notes")
        cls.project.members.add(cls.user)
        cls.project.datasets.add(dataset)
        cls.scan_report = ScanReport.objects.create(
            author=cls.user,
            name="SR",
            dataset="SR",
            visibility=VisibilityChoices.PUBLIC,
            parent_dataset=dataset,
        )
        cls.scan_report.editors.add(cls.user)

        for table, fields in OMOP_TABLES.items():
            omop_table = OmopTable.objects.create(table=table)
            for name in fields:
                OmopField.objects.create(table=omop_table, field=name)

        cls.condition = _concept(920001, "Myocardial infarction", "Condition")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)


class TestTableRoleRules(NoteTablesTestBase):
    def _rules(self, rules):
        return {
            (r.omop_field.table.table, r.omop_field.field): r.source_field_id
            for r in rules
        }

    def test_death_role_routes_to_death_table(self):
        death = ScanReportTable.objects.create(
            scan_report=self.scan_report, name="deaths.csv", table_role=TableRole.DEATH
        )
        cause = _field(death, "cause")
        death.person_id, death.date_event = _field(death, "p"), _field(death, "d")
        death.save()
        sr_concept = ScanReportConcept.objects.create(
            concept=self.condition,
            content_type=ContentType.objects.get_for_model(ScanReportField),
            object_id=cause.id,
        )

        rules = self._rules(save_mapping_rules(sr_concept))
        self.assertIn(("death", "cause_concept_id"), rules)
        self.assertNotIn(("condition_occurrence", "condition_concept_id"), rules)


class TestDeathTableFlag(NoteTablesTestBase):
    """API clients written before table roles can still use death_table."""

    def _edit(self, table, data):
        serializer = ScanReportTableEditSerializer(table, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        table.refresh_from_db()
        return serializer

    def test_reads_as_the_death_role(self):
        death = ScanReportTable.objects.create(
            scan_report=self.scan_report, name="deaths.csv", table_role=TableRole.DEATH
        )
        other = ScanReportTable.objects.create(
            scan_report=self.scan_report, name="labs.csv"
        )
        self.assertTrue(ScanReportTableListSerializerV2(death).data["death_table"])
        self.assertFalse(ScanReportTableListSerializerV2(other).data["death_table"])

    def test_setting_it_sets_the_role(self):
        table = ScanReportTable.objects.create(
            scan_report=self.scan_report, name="deaths.csv"
        )
        self._edit(table, {"death_table": True})
        self.assertEqual(table.table_role, TableRole.DEATH)
        self._edit(table, {"death_table": False})
        self.assertEqual(table.table_role, TableRole.STANDARD)

    def test_false_leaves_a_standard_table_alone(self):
        table = ScanReportTable.objects.create(
            scan_report=self.scan_report, name="labs.csv"
        )
        self._edit(table, {"death_table": False, "trigger_reuse": False})
        self.assertEqual(table.table_role, TableRole.STANDARD)
        self.assertFalse(table.trigger_reuse)

    def test_must_agree_with_table_role(self):
        table = ScanReportTable.objects.create(
            scan_report=self.scan_report, name="labs.csv"
        )
        serializer = ScanReportTableEditSerializer(
            table, data={"death_table": True, "table_role": "standard"}, partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("death_table", serializer.errors)
        # Agreeing values are fine
        self._edit(table, {"death_table": True, "table_role": "death"})
        self.assertEqual(table.table_role, TableRole.DEATH)


class TestTableRoleDatabaseDefault(TestCase):
    def test_raw_insert_without_role_is_standard(self):
        """
        Scan report tables are created with raw SQL when an upload is processed
        (Airflow's SR_processing), which doesn't set table_role.
        """
        from django.db import connection

        user = get_user_model().objects.create(username="sam", password="x")
        partner = DataPartner.objects.create(name="Shire")
        dataset = Dataset.objects.create(
            name="Upload", visibility=VisibilityChoices.PUBLIC, data_partner=partner
        )
        scan_report = ScanReport.objects.create(
            author=user, name="SR", dataset="SR", parent_dataset=dataset
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO mapping_scanreporttable (scan_report_id, name, created_at, updated_at, trigger_reuse)
                VALUES (%s, 'condition_occurrence', NOW(), NOW(), TRUE)
                RETURNING id
                """,
                [scan_report.id],
            )
            table_id = cursor.fetchone()[0]

        self.assertEqual(
            ScanReportTable.objects.get(id=table_id).table_role, TableRole.STANDARD
        )

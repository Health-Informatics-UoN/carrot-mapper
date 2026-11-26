"""
Note and note_nlp table roles: rule generation, the table field mappings API,
and death tables now being identified by role (with the deprecated
death_table API flag).

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
    MappingRule,
    NlpDerivedRecordExclusion,
    NlpLinkSettings,
    OmopField,
    OmopTable,
    Project,
    ScanReport,
    ScanReportConcept,
    ScanReportField,
    ScanReportTable,
    ScanReportTableFieldMapping,
    ScanReportValue,
    TableRole,
    VisibilityChoices,
)
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APIRequestFactory
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
    "note": [
        "note_id",
        "person_id",
        "note_datetime",
        "note_type_concept_id",
        "note_class_concept_id",
        "note_title",
        "note_text",
        "encoding_concept_id",
        "language_concept_id",
        "note_source_value",
        "note_event_id",
        "note_event_field_concept_id",
    ],
    "note_nlp": [
        "note_nlp_id",
        "note_id",
        "section_concept_id",
        "snippet",
        "offset",
        "lexical_variant",
        "note_nlp_concept_id",
        "note_nlp_source_concept_id",
        "nlp_system",
        "nlp_datetime",
        "term_exists",
        "term_temporal",
        "term_modifiers",
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

        # NLP output: one row per extracted SNOMED code
        cls.nlp = ScanReportTable.objects.create(
            scan_report=cls.scan_report, name="nlp.csv", table_role=TableRole.NOTE_NLP
        )
        cls.nlp_person = _field(cls.nlp, "patient_id", "INT")
        cls.nlp_date = _field(cls.nlp, "note_date")
        cls.nlp_code = _field(cls.nlp, "snomed_code")
        cls.nlp_note_ref = _field(cls.nlp, "note_ref")
        cls.nlp_term = _field(cls.nlp, "term")
        cls.nlp.person_id, cls.nlp.date_event = cls.nlp_person, cls.nlp_date
        cls.nlp.save()

        cls.notes = ScanReportTable.objects.create(
            scan_report=cls.scan_report, name="notes.csv", table_role=TableRole.NOTE
        )
        cls.notes_ref = _field(cls.notes, "note_ref")
        cls.notes_text = _field(cls.notes, "text")

        cls.condition = _concept(920001, "Myocardial infarction", "Condition")
        cls.qualifier = _concept(920002, "Left", "Qualifier Value")  # no OMOP table
        cls.class_concept = _concept(920003, "Clinic letter", "Note Type")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)


class TestNoteNlpRules(NoteTablesTestBase):
    def _value_concept(self, concept, value="x"):
        sr_value = ScanReportValue.objects.create(
            scan_report_field=self.nlp_code, value=value, frequency=1
        )
        return ScanReportConcept.objects.create(
            concept=concept,
            content_type=ContentType.objects.get_for_model(ScanReportValue),
            object_id=sr_value.id,
        )

    def _rules(self, rules):
        return {
            (r.omop_field.table.table, r.omop_field.field): r.source_field_id
            for r in rules
        }

    def test_concept_makes_note_nlp_and_domain_rules(self):
        rules = self._rules(save_mapping_rules(self._value_concept(self.condition)))

        code, date = self.nlp_code.id, self.nlp_date.id
        self.assertEqual(rules[("note_nlp", "note_nlp_concept_id")], code)
        self.assertEqual(rules[("note_nlp", "note_nlp_source_concept_id")], code)
        self.assertEqual(rules[("note_nlp", "nlp_datetime")], date)
        self.assertNotIn(("note_nlp", "person_id"), rules)
        # ...and the derived condition, as on any table
        self.assertEqual(rules[("condition_occurrence", "condition_concept_id")], code)
        self.assertEqual(
            rules[("condition_occurrence", "person_id")], self.nlp_person.id
        )

    def test_concept_without_domain_table_still_makes_note_nlp_rules(self):
        rules = self._rules(save_mapping_rules(self._value_concept(self.qualifier)))

        self.assertEqual(
            set(rules),
            {
                ("note_nlp", "note_nlp_concept_id"),
                ("note_nlp", "note_nlp_source_concept_id"),
                ("note_nlp", "nlp_datetime"),
            },
        )

    def test_api_accepts_concept_without_domain_table_on_note_nlp_table(self):
        response = self.client.post(
            "/api/v2/scanreports/concepts/",
            {
                "object_id": self.nlp_code.id,
                "concept": self.qualifier.concept_id,
                "content_type": "scanreportfield",
                "table_id": self.nlp.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(
            MappingRule.objects.filter(
                omop_field__table__table="note_nlp", concept__concept=self.qualifier
            ).count(),
            3,
        )

    def test_api_still_rejects_concept_without_domain_table_elsewhere(self):
        standard = ScanReportTable.objects.create(
            scan_report=self.scan_report, name="other.csv"
        )
        field = _field(standard, "code")
        standard.person_id, standard.date_event = (
            _field(standard, "p"),
            _field(standard, "d"),
        )
        standard.save()

        response = self.client.post(
            "/api/v2/scanreports/concepts/",
            {
                "object_id": field.id,
                "concept": self.qualifier.concept_id,
                "content_type": "scanreportfield",
                "table_id": standard.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

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


class TestTableFieldMappingsApi(NoteTablesTestBase):
    def _url(self, table):
        return f"/api/v2/scanreports/{self.scan_report.id}/tables/{table.id}/field-mappings/"

    def _put(self, table, body):
        return self.client.put(self._url(table), body, format="json")

    def test_put_and_get_note_mappings(self):
        body = [
            {"omop_field": "note_id", "source_field": self.notes_ref.id},
            {"omop_field": "note_text", "source_field": self.notes_text.id},
            {
                "omop_field": "note_class_concept_id",
                "constant_value": str(self.class_concept.concept_id),
            },
        ]
        response = self._put(self.notes, body)
        self.assertEqual(response.status_code, 200, response.content)

        listed = self.client.get(self._url(self.notes)).json()
        self.assertEqual(
            listed["mappings"],
            [
                {
                    "omop_field": "note_class_concept_id",
                    "source_field": None,
                    "constant_value": str(self.class_concept.concept_id),
                    "concept_name": "Clinic letter",
                },
                {
                    "omop_field": "note_id",
                    "source_field": self.notes_ref.id,
                    "constant_value": None,
                    "concept_name": None,
                },
                {
                    "omop_field": "note_text",
                    "source_field": self.notes_text.id,
                    "constant_value": None,
                    "concept_name": None,
                },
            ],
        )
        # The fields the note role can map, for building the form
        fields = {f["omop_field"]: f for f in listed["fields"]}
        self.assertEqual(
            fields["note_id"],
            {
                "omop_field": "note_id",
                "required": True,
                "source": True,
                "constant": False,
                "concept": False,
            },
        )
        self.assertTrue(fields["language_concept_id"]["concept"])
        self.assertNotIn("lexical_variant", fields)

        # PUT replaces the whole set
        body[2] = {"omop_field": "note_title", "constant_value": "Letter"}
        self.assertEqual(self._put(self.notes, body).status_code, 200)
        self.assertEqual(
            sorted(
                m["omop_field"]
                for m in self.client.get(self._url(self.notes)).json()["mappings"]
            ),
            ["note_id", "note_text", "note_title"],
        )

    def test_note_nlp_constant_text_field(self):
        response = self._put(
            self.nlp,
            [
                {"omop_field": "note_id", "source_field": self.nlp_note_ref.id},
                {"omop_field": "lexical_variant", "source_field": self.nlp_term.id},
                {"omop_field": "nlp_system", "constant_value": "MedCAT 1.12"},
            ],
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_validation_errors(self):
        required = [
            {"omop_field": "note_id", "source_field": self.notes_ref.id},
            {"omop_field": "note_text", "source_field": self.notes_text.id},
        ]
        cases = {
            "field not allowed for role": {
                "omop_field": "lexical_variant",
                "constant_value": "x",
            },
            "both source and constant": {
                "omop_field": "note_title",
                "source_field": self.notes_text.id,
                "constant_value": "x",
            },
            "neither source nor constant": {"omop_field": "note_title"},
            "unknown concept": {
                "omop_field": "language_concept_id",
                "constant_value": "123",
            },
            "concept field from source": {
                "omop_field": "language_concept_id",
                "source_field": self.notes_text.id,
            },
            "key field as constant": {
                "omop_field": "note_event_id",
                "constant_value": "1",
            },
            "source field of another table": {
                "omop_field": "note_title",
                "source_field": self.nlp_term.id,
            },
        }
        for name, item in cases.items():
            with self.subTest(name):
                response = self._put(self.notes, required + [item])
                self.assertEqual(response.status_code, 400, response.content)

        missing = self._put(self.notes, required[:1])
        self.assertEqual(
            missing.json(),
            {
                "detail": "Required fields missing: note_text.",
                "duplicated": [],
                "missing_required": ["note_text"],
            },
        )
        # Validation errors come back as one readable message for the client
        unknown = self._put(
            self.notes,
            required + [{"omop_field": "language_concept_id", "constant_value": "123"}],
        )
        self.assertEqual(
            unknown.json()["detail"],
            "constant_value: 'language_concept_id': '123' is not a known concept id.",
        )
        self.assertFalse(ScanReportTableFieldMapping.objects.exists())

    def test_standard_table_has_no_field_mappings(self):
        standard = ScanReportTable.objects.create(
            scan_report=self.scan_report, name="s.csv"
        )
        response = self._put(standard, [])
        self.assertEqual(response.status_code, 400)

    def test_changing_role_clears_field_mappings(self):
        from api.serializers import ScanReportTableEditSerializer

        self._put(
            self.notes,
            [
                {"omop_field": "note_id", "source_field": self.notes_ref.id},
                {"omop_field": "note_text", "source_field": self.notes_text.id},
            ],
        )
        serializer = ScanReportTableEditSerializer(
            self.notes,
            data={"table_role": TableRole.NOTE},
            partial=True,
            context={"request": APIRequestFactory().patch("/")},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.assertEqual(self.notes.field_mappings.count(), 2)

        serializer = ScanReportTableEditSerializer(
            self.notes,
            data={"table_role": TableRole.STANDARD},
            partial=True,
            context={"request": APIRequestFactory().patch("/")},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.assertEqual(self.notes.field_mappings.count(), 0)


class TestNlpSettingsApi(NoteTablesTestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.nlp_negated = _field(cls.nlp, "negated")
        cls.nlp_experiencer = _field(cls.nlp, "experiencer")
        cls.note_domain = _concept(920010, "Note", "Metadata")
        cls.derived = _concept(920011, "Has NLP finding", "Relationship")
        cls.derived_reverse = _concept(920012, "NLP finding of", "Relationship")

    def _url(self, table):
        return (
            f"/api/v2/scanreports/{self.scan_report.id}/tables/{table.id}/nlp-settings/"
        )

    def _put(self, table, body):
        return self.client.put(self._url(table), body, format="json")

    def _body(self, **overrides):
        body = {
            "source_domain_concept": self.note_domain.concept_id,
            "relationship_concept": self.derived.concept_id,
            "reverse_relationship_concept": self.derived_reverse.concept_id,
            "exclusions": [
                {
                    "source_field": self.nlp_negated.id,
                    "excluded_values": ["true", " 1 ", "1"],
                },
                {
                    "source_field": self.nlp_experiencer.id,
                    "excluded_values": ["family"],
                },
            ],
        }
        body.update(overrides)
        return body

    def test_empty_settings(self):
        self.assertEqual(
            self.client.get(self._url(self.nlp)).json(),
            {
                "source_domain_concept": None,
                "relationship_concept": None,
                "reverse_relationship_concept": None,
                "exclusions": [],
            },
        )

    def test_put_and_get(self):
        response = self._put(self.nlp, self._body())
        self.assertEqual(response.status_code, 200, response.content)

        settings = self.client.get(self._url(self.nlp)).json()
        self.assertEqual(
            settings["relationship_concept"],
            {"concept_id": 920011, "concept_name": "Has NLP finding"},
        )
        self.assertEqual(
            settings["exclusions"],
            [
                {
                    "source_field": self.nlp_experiencer.id,
                    "source_field_name": "experiencer",
                    "excluded_values": ["family"],
                },
                {
                    "source_field": self.nlp_negated.id,
                    "source_field_name": "negated",
                    "excluded_values": ["true", "1"],  # trimmed, deduplicated
                },
            ],
        )

        # PUT replaces everything; links can be turned off
        response = self._put(
            self.nlp,
            self._body(
                source_domain_concept=None,
                relationship_concept=None,
                reverse_relationship_concept=None,
                exclusions=[],
            ),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(
            NlpLinkSettings.objects.get(scan_report_table=self.nlp).is_complete
        )
        self.assertFalse(NlpDerivedRecordExclusion.objects.exists())

    def test_validation_errors(self):
        cases = {
            "partial link": self._body(reverse_relationship_concept=None),
            "unknown concept": self._body(relationship_concept=123),
            "field of another table": self._body(
                exclusions=[
                    {"source_field": self.notes_text.id, "excluded_values": ["x"]}
                ]
            ),
            "no values": self._body(
                exclusions=[
                    {"source_field": self.nlp_negated.id, "excluded_values": [" "]}
                ]
            ),
            "same field twice": self._body(
                exclusions=[
                    {"source_field": self.nlp_negated.id, "excluded_values": ["a"]},
                    {"source_field": self.nlp_negated.id, "excluded_values": ["b"]},
                ]
            ),
        }
        for name, body in cases.items():
            with self.subTest(name):
                response = self._put(self.nlp, body)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertTrue(response.json()["detail"])
        self.assertFalse(NlpLinkSettings.objects.exists())

    def test_only_note_nlp_tables(self):
        response = self._put(self.notes, self._body(exclusions=[]))
        self.assertEqual(response.status_code, 400)

    def test_viewers_cannot_change_settings(self):
        viewer = get_user_model().objects.create(username="pippin", password="x")
        self.scan_report.viewers.add(viewer)
        self.project.members.add(viewer)
        self.client.force_authenticate(viewer)

        self.assertEqual(self.client.get(self._url(self.nlp)).status_code, 200)
        self.assertEqual(self._put(self.nlp, self._body()).status_code, 403)

    def test_changing_role_clears_nlp_settings(self):
        from api.serializers import ScanReportTableEditSerializer

        self._put(self.nlp, self._body())
        serializer = ScanReportTableEditSerializer(
            self.nlp,
            data={"table_role": TableRole.STANDARD},
            partial=True,
            context={"request": APIRequestFactory().patch("/")},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self.assertFalse(NlpLinkSettings.objects.exists())
        self.assertFalse(NlpDerivedRecordExclusion.objects.exists())


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

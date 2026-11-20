"""
Rules export for `<domain>_source_concept_id` fields (#1006).

A ScanReportConcept may record the source vocabulary concept its standard
concept was mapped from. The source concept id field must export that concept,
while the other concept id fields keep exporting the standard concept. When no
source concept is recorded the export falls back to the mapped concept, which
is the behaviour from before the field existed.
"""

from datetime import date

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
    ScanReport,
    ScanReportConcept,
    ScanReportField,
    ScanReportTable,
    ScanReportValue,
)
from services.rules import _get_omop_field
from services.rules_export import (
    get_mapping_rules_as_csv,
    get_mapping_rules_json,
    get_mapping_rules_list,
    source_concept_id_for,
)

# Made-up ids, well clear of anything the other tests create.
SNOMED_SOURCE_ID = 9900001
STANDARD_ID = 9900002
OTHER_STANDARD_ID = 9900003


def _concept(concept_id, name, vocabulary, standard):
    return Concept.objects.create(
        concept_id=concept_id,
        concept_name=name,
        domain_id="Condition",
        vocabulary_id=vocabulary,
        concept_class_id="Clinical Finding",
        standard_concept=standard,
        concept_code=str(concept_id),
        valid_start_date=date(2000, 1, 1),
        valid_end_date=date(2099, 12, 31),
    )


def _field(table, name, type_column="VARCHAR"):
    return ScanReportField.objects.create(
        scan_report_table=table,
        name=name,
        description_column="",
        type_column=type_column,
    )


class TestSourceConceptExport(TestCase):
    def setUp(self):
        _get_omop_field.cache_clear()

        user = get_user_model().objects.create(username="nlp", password="x")
        partner = DataPartner.objects.create(name="Partner")
        dataset = Dataset.objects.create(
            name="Dataset", visibility="PUBLIC", data_partner=partner
        )
        self.scan_report = ScanReport.objects.create(
            author=user, name="SR", dataset="SR dataset", parent_dataset=dataset
        )
        table = ScanReportTable.objects.create(
            scan_report=self.scan_report, name="nlp.csv"
        )
        person = _field(table, "person_id", "INT")
        note_date = _field(table, "note_date")
        self.code_field = _field(table, "snomed_code")
        table.person_id = person
        table.date_event = note_date
        table.save()

        omop_table = OmopTable.objects.create(table="condition_occurrence")
        self.omop_fields = {
            name: OmopField.objects.create(table=omop_table, field=name)
            for name in [
                "condition_concept_id",
                "condition_source_concept_id",
                "condition_source_value",
            ]
        }

        self.snomed_source = _concept(
            SNOMED_SOURCE_ID, "Inactive finding", "SNOMED", None
        )
        self.standard = _concept(STANDARD_ID, "Active finding", "SNOMED", "S")
        _concept(OTHER_STANDARD_ID, "Manual finding", "SNOMED", "S")

        value_ct = ContentType.objects.get(app_label="mapping", model="scanreportvalue")
        self.value_with_source = ScanReportValue.objects.create(
            value="111", frequency=10, scan_report_field=self.code_field
        )
        self.value_manual = ScanReportValue.objects.create(
            value="222", frequency=5, scan_report_field=self.code_field
        )

        self.vocab_concept = ScanReportConcept.objects.create(
            concept=self.standard,
            source_concept=self.snomed_source,
            content_type=value_ct,
            object_id=self.value_with_source.id,
            creation_type="V",
        )
        self.manual_concept = ScanReportConcept.objects.create(
            concept_id=OTHER_STANDARD_ID,
            content_type=value_ct,
            object_id=self.value_manual.id,
            creation_type="M",
        )
        for sr_concept in (self.vocab_concept, self.manual_concept):
            for omop_field in self.omop_fields.values():
                MappingRule.objects.create(
                    scan_report=self.scan_report,
                    omop_field=omop_field,
                    source_field=self.code_field,
                    concept=sr_concept,
                    approved=True,
                )

    def _rules(self):
        return MappingRule.objects.filter(scan_report=self.scan_report).order_by("id")

    def test_source_concept_id_for(self):
        self.assertEqual(source_concept_id_for(self.vocab_concept), SNOMED_SOURCE_ID)
        self.assertEqual(source_concept_id_for(self.manual_concept), OTHER_STANDARD_ID)

    def test_rules_list_term_mappings(self):
        by_key = {
            (rule["rule_id"], rule["destination_field"].field): rule["term_mapping"]
            for rule in get_mapping_rules_list(self._rules())
        }
        vocab, manual = self.vocab_concept.id, self.manual_concept.id

        self.assertEqual(
            by_key[(vocab, "condition_source_concept_id")], {"111": SNOMED_SOURCE_ID}
        )
        self.assertEqual(by_key[(vocab, "condition_concept_id")], {"111": STANDARD_ID})
        self.assertIsNone(by_key[(vocab, "condition_source_value")])

        # No source concept recorded: unchanged behaviour
        self.assertEqual(
            by_key[(manual, "condition_source_concept_id")], {"222": OTHER_STANDARD_ID}
        )
        self.assertEqual(
            by_key[(manual, "condition_concept_id")], {"222": OTHER_STANDARD_ID}
        )

    def test_rules_json_keeps_one_entry_per_concept(self):
        cdm = get_mapping_rules_json(self._rules())["cdm"]["condition_occurrence"]
        entry = cdm[f"Active finding {self.vocab_concept.id}"]

        self.assertEqual(
            entry["condition_source_concept_id"]["term_mapping"],
            {"111": SNOMED_SOURCE_ID},
        )
        self.assertEqual(
            entry["condition_concept_id"]["term_mapping"], {"111": STANDARD_ID}
        )
        self.assertNotIn("term_mapping", entry["condition_source_value"])

    def test_csv_describes_source_concept_on_its_row(self):
        rows = get_mapping_rules_as_csv(self._rules()).read().splitlines()
        header = rows[0].split(",")
        records = [dict(zip(header, row.split(","))) for row in rows[1:]]

        exported_ids = {r["concept_id"] for r in records if r["source_value"] == "111"}
        self.assertEqual(exported_ids, {str(SNOMED_SOURCE_ID), str(STANDARD_ID)})

        source_row = next(
            r for r in records if r["concept_id"] == str(SNOMED_SOURCE_ID)
        )
        # Non-standard source concept: blank "concept" (standard flag) column
        self.assertEqual(source_row["concept"], "None")
        self.assertEqual(source_row["vocabulary"], "SNOMED")

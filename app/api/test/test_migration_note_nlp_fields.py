import importlib

from django.apps import apps
from django.test import TestCase
from mapping.models import OmopField, OmopTable

migration = importlib.import_module("mapping.migrations.0019_fix_note_nlp_omop_fields")


class TestFixNoteNlpOmopFields(TestCase):
    def _make_table(self, field_names):
        table = OmopTable.objects.create(table="note_nlp")
        for name in field_names:
            OmopField.objects.create(table=table, field=name)
        return table

    def _field_names(self, table):
        return list(
            OmopField.objects.filter(table=table)
            .order_by("id")
            .values_list("field", flat=True)
        )

    def test_renames_corrupted_rows(self):
        table = self._make_table(migration.NOTE_NLP_REQUIRED_FLAGS)

        migration.fix_note_nlp_fields(apps, None)

        self.assertEqual(self._field_names(table), migration.NOTE_NLP_FIELDS)

    def test_correct_rows_are_left_alone(self):
        table = self._make_table(migration.NOTE_NLP_FIELDS)

        migration.fix_note_nlp_fields(apps, None)

        self.assertEqual(self._field_names(table), migration.NOTE_NLP_FIELDS)

    def test_partially_edited_rows_are_left_alone(self):
        partially_fixed = ["note_nlp_id"] + migration.NOTE_NLP_REQUIRED_FLAGS[1:]
        table = self._make_table(partially_fixed)

        migration.fix_note_nlp_fields(apps, None)

        self.assertEqual(self._field_names(table), partially_fixed)

    def test_other_tables_are_untouched(self):
        other = OmopTable.objects.create(table="note")
        OmopField.objects.create(table=other, field="yes")

        migration.fix_note_nlp_fields(apps, None)

        self.assertEqual(self._field_names(other), ["yes"])

    def test_fixture_note_nlp_fields_are_named(self):
        """The shipped fixture must seed real column names for note_nlp."""
        import json
        from pathlib import Path

        import mapping

        fixture = Path(mapping.__file__).parent / "fixtures" / "mapping.json"
        rows = json.loads(fixture.read_text())
        note_nlp_pks = [
            r["pk"]
            for r in rows
            if r["model"] == "mapping.omoptable" and r["fields"]["table"] == "note_nlp"
        ]
        names = [
            r["fields"]["field"]
            for r in sorted(rows, key=lambda r: r["pk"])
            if r["model"] == "mapping.omopfield"
            and r["fields"]["table"] in note_nlp_pks
        ]
        self.assertEqual(names, migration.NOTE_NLP_FIELDS)

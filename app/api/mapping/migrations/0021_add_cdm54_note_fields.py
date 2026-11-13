"""
Add the OMOP CDM v5.4 ``note`` columns to the seeded OMOP schema metadata.

The ``mapping`` fixture describes CDM v5.3, which lacks ``note_event_id`` and
``note_event_field_concept_id``. The fixture now includes them for fresh seeds
(which happen after migrations run); this adds them to databases seeded before.
"""

from django.db import migrations

NOTE_V54_FIELDS = ["note_event_id", "note_event_field_concept_id"]


def add_note_fields(apps, schema_editor):
    OmopTable = apps.get_model("mapping", "OmopTable")
    OmopField = apps.get_model("mapping", "OmopField")

    for table in OmopTable.objects.filter(table="note"):
        for name in NOTE_V54_FIELDS:
            OmopField.objects.get_or_create(table=table, field=name)


def remove_note_fields(apps, schema_editor):
    OmopField = apps.get_model("mapping", "OmopField")
    OmopField.objects.filter(table__table="note", field__in=NOTE_V54_FIELDS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("mapping", "0020_scanreportconcept_source_concept"),
    ]

    operations = [
        migrations.RunPython(add_note_fields, remove_note_fields),
    ]

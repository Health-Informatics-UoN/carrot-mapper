"""
Repair the OmopField rows seeded for the OMOP ``note_nlp`` table.

The original ``mapping`` fixture loaded the CDM v5.3 "is required" column
("yes"/"no") into ``OmopField.field`` for every ``note_nlp`` column instead of
the column name, so none of the ``note_nlp`` fields could be looked up by name.

The 14 corrupted rows were created in CDM DDL column order, and their yes/no
values match the NOT NULL pattern of the v5.3 ``note_nlp`` DDL exactly, so the
correct name for each row is recovered from its position when ordered by id.

The migration only touches the table when it still holds exactly the 14
corrupted rows, so it is a no-op on fresh databases seeded from the corrected
fixture and on databases that were already fixed by hand.
"""

from django.db import migrations

NOTE_NLP_FIELDS = [
    "note_nlp_id",
    "note_id",
    "section_concept_id",
    "snippet",
    "offset",
    "lexical_variant",
    "note_nlp_concept_id",
    "note_nlp_source_concept_id",
    "nlp_system",
    "nlp_date",
    "nlp_datetime",
    "term_exists",
    "term_temporal",
    "term_modifiers",
]

# The "is required" flags from the v5.3 DDL, in the same order. Used to confirm
# the corrupted rows line up with NOTE_NLP_FIELDS before renaming anything.
NOTE_NLP_REQUIRED_FLAGS = [
    "yes",
    "yes",
    "no",
    "no",
    "no",
    "yes",
    "no",
    "no",
    "no",
    "yes",
    "no",
    "no",
    "no",
    "no",
]


def fix_note_nlp_fields(apps, schema_editor):
    OmopTable = apps.get_model("mapping", "OmopTable")
    OmopField = apps.get_model("mapping", "OmopField")

    for table in OmopTable.objects.filter(table="note_nlp"):
        fields = list(OmopField.objects.filter(table=table).order_by("id"))
        if [f.field for f in fields] != NOTE_NLP_REQUIRED_FLAGS:
            # Already correct, partially edited, or seeded differently: leave it.
            continue
        for omop_field, name in zip(fields, NOTE_NLP_FIELDS):
            omop_field.field = name
            omop_field.save(update_fields=["field"])


class Migration(migrations.Migration):
    dependencies = [
        ("mapping", "0019_scanreport_uuid"),
    ]

    operations = [
        migrations.RunPython(fix_note_nlp_fields, migrations.RunPython.noop),
    ]

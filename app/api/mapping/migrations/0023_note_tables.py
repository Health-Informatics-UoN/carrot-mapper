"""
Note tables: the "note" table role, the OMOP CDM v5.4 note fields, and
ScanReportTableFieldMapping.

The ``mapping`` fixture describes CDM v5.3, which lacks ``note_event_id`` and
``note_event_field_concept_id``. The fixture now includes them for fresh seeds
(which happen after migrations run); this adds them to databases seeded before.
"""

import django.db.models.deletion
from django.db import migrations, models

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
        ("mapping", "0022_scanreporttable_table_role"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scanreporttable",
            name="table_role",
            field=models.CharField(
                choices=[
                    ("standard", "Standard"),
                    ("death", "Death"),
                    ("note", "Note"),
                ],
                db_default="standard",
                default="standard",
                help_text="What this table's rows become in the OMOP CDM",
                max_length=16,
            ),
        ),
        migrations.RunPython(add_note_fields, remove_note_fields),
        migrations.CreateModel(
            name="ScanReportTableFieldMapping",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "constant_value",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "omop_field",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="mapping.omopfield",
                    ),
                ),
                (
                    "scan_report_table",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="field_mappings",
                        to="mapping.scanreporttable",
                    ),
                ),
                (
                    "source_field",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="mapping.scanreportfield",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("scan_report_table", "omop_field"),
                        name="sr_table_field_mapping_unique",
                    )
                ],
            },
        ),
    ]

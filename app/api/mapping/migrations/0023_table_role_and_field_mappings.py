"""
Replace ScanReportTable.death_table with table_role, add type_concept, and add
ScanReportTableFieldMapping.

Tables flagged as death tables get the "death" role; every other table gets
"standard". Reversing restores death_table from the role (note and note_nlp
roles become non-death tables).
"""

import django.db.models.deletion
from django.db import migrations, models


def death_table_to_role(apps, schema_editor):
    ScanReportTable = apps.get_model("mapping", "ScanReportTable")
    ScanReportTable.objects.filter(death_table=True).update(table_role="death")


def role_to_death_table(apps, schema_editor):
    ScanReportTable = apps.get_model("mapping", "ScanReportTable")
    ScanReportTable.objects.filter(table_role="death").update(death_table=True)


class Migration(migrations.Migration):
    dependencies = [
        ("data", "__first__"),
        ("mapping", "0022_add_cdm54_note_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="scanreporttable",
            name="table_role",
            field=models.CharField(
                choices=[
                    ("standard", "Standard"),
                    ("death", "Death"),
                    ("note", "Note"),
                    ("note_nlp", "Note NLP"),
                ],
                default="standard",
                help_text="What this table's rows become in the OMOP CDM",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="scanreporttable",
            name="type_concept",
            field=models.ForeignKey(
                blank=True,
                help_text="Type concept for every record built from this table",
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="data.concept",
            ),
        ),
        migrations.RunPython(death_table_to_role, role_to_death_table),
        migrations.RemoveField(
            model_name="scanreporttable",
            name="death_table",
        ),
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

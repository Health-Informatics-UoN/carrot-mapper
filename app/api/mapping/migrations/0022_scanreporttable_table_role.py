"""
Replace ScanReportTable.death_table with table_role, and add type_concept.

Tables flagged as death tables get the "death" role; every other table gets
"standard". Reversing restores death_table from the role. table_role has a
database default because Airflow inserts scan report tables with raw SQL.
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
        ("mapping", "0021_scanreportconcept_source_concept"),
    ]

    operations = [
        migrations.AddField(
            model_name="scanreporttable",
            name="table_role",
            field=models.CharField(
                choices=[
                    ("standard", "Standard"),
                    ("death", "Death"),
                ],
                db_default="standard",
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
    ]

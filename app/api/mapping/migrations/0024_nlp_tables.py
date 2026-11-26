"""
Note NLP tables: the "note_nlp" table role, and the settings for records
derived from them (fact_relationship links and exclusions).
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("data", "__first__"),
        ("mapping", "0023_note_tables"),
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
                    ("note_nlp", "Note NLP"),
                ],
                db_default="standard",
                default="standard",
                help_text="What this table's rows become in the OMOP CDM",
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="NlpLinkSettings",
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
                    "relationship_concept",
                    models.ForeignKey(
                        blank=True,
                        help_text="Relationship from a note_nlp record to a record derived from it",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="data.concept",
                    ),
                ),
                (
                    "reverse_relationship_concept",
                    models.ForeignKey(
                        blank=True,
                        help_text="Relationship from a derived record back to its note_nlp record",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="data.concept",
                    ),
                ),
                (
                    "scan_report_table",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nlp_link",
                        to="mapping.scanreporttable",
                    ),
                ),
                (
                    "source_domain_concept",
                    models.ForeignKey(
                        blank=True,
                        help_text="Domain concept for note_nlp records in fact_relationship",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="data.concept",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="NlpDerivedRecordExclusion",
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
                ("excluded_values", models.JSONField(default=list)),
                (
                    "scan_report_table",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nlp_exclusions",
                        to="mapping.scanreporttable",
                    ),
                ),
                (
                    "source_field",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="mapping.scanreportfield",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("scan_report_table", "source_field"),
                        name="nlp_exclusion_unique_field",
                    )
                ],
            },
        ),
    ]

# Generated by Django 5.2.1 on 2025-06-25 12:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mapping", "0008_remove_scanreportfield_fraction_empty_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scanreport",
            name="file",
            field=models.FileField(default="None", null=True, blank=True),
        ),
        migrations.DeleteModel(
            name="ClassificationSystem",
        ),
        migrations.DeleteModel(
            name="NLPModel",
        ),
        migrations.RemoveField(
            model_name="mappingrule",
            name="source_table",
        ),
        migrations.RemoveField(
            model_name="scanreport",
            name="file",
        ),
        migrations.RemoveField(
            model_name="scanreportconcept",
            name="nlp_concept_code",
        ),
        migrations.RemoveField(
            model_name="scanreportconcept",
            name="nlp_confidence",
        ),
        migrations.RemoveField(
            model_name="scanreportconcept",
            name="nlp_entity",
        ),
        migrations.RemoveField(
            model_name="scanreportconcept",
            name="nlp_entity_type",
        ),
        migrations.RemoveField(
            model_name="scanreportconcept",
            name="nlp_processed_string",
        ),
        migrations.RemoveField(
            model_name="scanreportconcept",
            name="nlp_vocabulary",
        ),
        migrations.RemoveField(
            model_name="scanreportfield",
            name="concept_id",
        ),
        migrations.DeleteModel(
            name="ScanReportAssertion",
        ),
    ]

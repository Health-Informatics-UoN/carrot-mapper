# Generated by Django 5.2.1 on 2025-06-26 09:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0002_remove_job_scan_report_id_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="details",
            field=models.TextField(blank=True, null=True),
        ),
    ]

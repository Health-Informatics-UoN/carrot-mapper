# Generated by Django 5.2.1 on 2025-06-19 11:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("mapping", "0007_alter_dataset_hidden_alter_mappingstatus_value_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="scanreportfield",
            name="fraction_empty",
        ),
        migrations.RemoveField(
            model_name="scanreportfield",
            name="fraction_unique",
        ),
        migrations.RemoveField(
            model_name="scanreportfield",
            name="max_length",
        ),
        migrations.RemoveField(
            model_name="scanreportfield",
            name="nrows",
        ),
        migrations.RemoveField(
            model_name="scanreportfield",
            name="nrows_checked",
        ),
        migrations.RemoveField(
            model_name="scanreportfield",
            name="nunique_values",
        ),
    ]

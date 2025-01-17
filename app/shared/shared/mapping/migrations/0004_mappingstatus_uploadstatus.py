# Generated by Django 4.2.13 on 2024-10-15 08:51

from django.db import migrations, models


def create_status_objects(apps, schema_editor):
    UploadStatus = apps.get_model("mapping", "UploadStatus")
    MappingStatus = apps.get_model("mapping", "MappingStatus")

    # Create UploadStatus objects
    upload_statuses = [
        {"id": 1, "value": "IN_PROGRESS", "display_name": "Upload in Progress"},
        {"id": 2, "value": "COMPLETE", "display_name": "Upload Complete"},
        {"id": 3, "value": "FAILED", "display_name": "Upload Failed"},
    ]

    for status in upload_statuses:
        UploadStatus.objects.create(
            id=status["id"], value=status["value"], display_name=status["display_name"]
        )

    # Create MappingStatus objects
    mapping_statuses = [
        {"id": 1, "value": "PENDING", "display_name": "Pending Mapping"},
        {"id": 2, "value": "MAPPING_25PERCENT", "display_name": "Mapping 25%"},
        {"id": 3, "value": "MAPPING_50PERCENT", "display_name": "Mapping 50%"},
        {"id": 4, "value": "MAPPING_75PERCENT", "display_name": "Mapping 75%"},
        {"id": 5, "value": "COMPLETE", "display_name": "Mapping Complete"},
        {"id": 6, "value": "BLOCKED", "display_name": "Blocked"},
    ]

    for status in mapping_statuses:
        MappingStatus.objects.create(
            id=status["id"], value=status["value"], display_name=status["display_name"]
        )


def remove_status_objects(apps, schema_editor):
    UploadStatus = apps.get_model("mapping", "UploadStatus")
    MappingStatus = apps.get_model("mapping", "MappingStatus")

    # Remove all UploadStatus objects
    UploadStatus.objects.all().delete()

    # Remove all MappingStatus objects
    MappingStatus.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("mapping", "0003_handmade_20220428_1503"),
    ]

    operations = [
        migrations.CreateModel(
            name="MappingStatus",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("value", models.CharField(max_length=64)),
                ("display_name", models.CharField(max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name="UploadStatus",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("value", models.CharField(max_length=64)),
                ("display_name", models.CharField(max_length=64)),
            ],
        ),
        migrations.RunPython(create_status_objects, remove_status_objects),
    ]

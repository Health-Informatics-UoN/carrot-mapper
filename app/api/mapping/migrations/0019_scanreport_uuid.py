import uuid

from django.db import migrations, models


def fill_uuids(apps, schema_editor):
    ScanReport = apps.get_model("mapping", "ScanReport")
    reports = list(ScanReport.objects.filter(uuid__isnull=True).only("pk"))
    for report in reports:
        report.uuid = uuid.uuid4()
    ScanReport.objects.bulk_update(reports, ["uuid"], batch_size=1000)


class Migration(migrations.Migration):
    dependencies = [
        ("mapping", "0018_alter_scanreportconcept_creation_type"),
    ]

    # Added nullable, filled with a distinct value per row, then made unique:
    # a callable default on AddField would give every existing row the same one.
    operations = [
        migrations.AddField(
            model_name="scanreport",
            name="uuid",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(fill_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="scanreport",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
    ]

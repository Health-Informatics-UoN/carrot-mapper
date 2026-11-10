from django.db import migrations

SSSOM_VALUE = "mapping_sssom"
SSSOM_DISPLAY_NAME = "Mapping Rules SSSOM"


def add_sssom_filetype(apps, schema_editor):
    """
    Add the SSSOM file type to existing deployments.

    Fresh databases are seeded from fixtures/filetypes.json by the
    `automatic_seeding_data` command, which only runs when the table is empty - so
    don't insert anything here on an empty table, or the fixture would be skipped.
    """
    FileType = apps.get_model("files", "FileType")
    if not FileType.objects.exists():
        return
    FileType.objects.get_or_create(
        value=SSSOM_VALUE, defaults={"display_name": SSSOM_DISPLAY_NAME}
    )


def remove_sssom_filetype(apps, schema_editor):
    FileType = apps.get_model("files", "FileType")
    FileType.objects.filter(value=SSSOM_VALUE).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("files", "0002_alter_filedownload_id_alter_filetype_id"),
    ]

    operations = [
        migrations.RunPython(add_sssom_filetype, remove_sssom_filetype),
    ]

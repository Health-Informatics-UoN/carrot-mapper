from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mapping", "0025_scanreporttablefieldmapping_map_values"),
    ]

    operations = [
        migrations.AddField(
            model_name="scanreporttablefieldmapping",
            name="vocabulary_id",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]

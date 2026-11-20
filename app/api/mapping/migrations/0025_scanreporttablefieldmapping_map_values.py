from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mapping", "0024_scanreporttable_table_role_db_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="scanreporttablefieldmapping",
            name="map_values",
            field=models.BooleanField(db_default=False, default=False),
        ),
    ]

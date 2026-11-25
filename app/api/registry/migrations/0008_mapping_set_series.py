import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mapping", "0019_scanreport_uuid"),
        ("registry", "0007_prefix_and_publisher"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MappingSetSeries",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("set_uri", models.CharField(max_length=500, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "publisher",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="registry_mapping_set_series",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source_scan_report",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="registry_mapping_set_series",
                        to="mapping.scanreport",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddField(
            model_name="mappingset",
            name="series",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="versions",
                to="registry.mappingsetseries",
            ),
        ),
        migrations.AlterField(
            model_name="mappingset",
            name="series",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="versions",
                to="registry.mappingsetseries",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="mappingset",
            name="registry_mappingset_uri_version_uniq",
        ),
        migrations.RemoveIndex(
            model_name="mappingset",
            name="registry_ma_set_uri_c08128_idx",
        ),
        migrations.RemoveField(model_name="mappingset", name="set_uri"),
        migrations.AddConstraint(
            model_name="mappingset",
            constraint=models.UniqueConstraint(
                fields=("series", "set_version"),
                name="registry_mappingset_series_version_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="mappingset",
            index=models.Index(
                fields=["series", "created_at"],
                name="registry_ma_series__a2206a_idx",
            ),
        ),
    ]

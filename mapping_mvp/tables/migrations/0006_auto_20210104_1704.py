# Generated by Django 3.1.5 on 2021-01-04 17:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tables', '0005_auto_20210104_1704'),
    ]

    operations = [
        migrations.AlterField(
            model_name='localdb',
            name='term',
            field=models.CharField(max_length=256),
        ),
    ]

# Generated by Django 3.1.5 on 2021-01-04 16:56

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('tables', '0003_omopmapping'),
    ]

    operations = [
        migrations.CreateModel(
            name='controlledVocab',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('term', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tables.localdb', unique=True)),
            ],
        ),
        migrations.AlterField(
            model_name='omopmapping',
            name='controlled_vocab_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tables.controlledvocab'),
        ),
        migrations.DeleteModel(
            name='vocab',
        ),
    ]

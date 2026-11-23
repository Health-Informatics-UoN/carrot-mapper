from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mapping", "0024_nlp_link_settings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scanreporttable",
            name="table_role",
            field=models.CharField(
                choices=[
                    ("standard", "Standard"),
                    ("death", "Death"),
                    ("note", "Note"),
                    ("note_nlp", "Note NLP"),
                ],
                db_default="standard",
                default="standard",
                help_text="What this table's rows become in the OMOP CDM",
                max_length=16,
            ),
        ),
    ]

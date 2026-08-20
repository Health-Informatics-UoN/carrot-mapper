from django.db import migrations


def backfill_profiles(apps, schema_editor):
    """
    The `Profile` model is created for new users via a `post_save` signal
    (see `api/signals.py`), which does not run for users that already
    existed before this feature shipped. Backfill a `Profile` for them.
    """
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("users", "Profile")

    for user in User.objects.all():
        Profile.objects.get_or_create(user=user)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_profiles, migrations.RunPython.noop),
    ]

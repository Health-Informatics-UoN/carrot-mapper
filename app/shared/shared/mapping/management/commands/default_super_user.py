
"""command to create a default superuser iff no users exist"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
import django
import os


class Command(BaseCommand):
    """create a default superuser iff no users exist"""

    help = "create a default superuser iff no users exist"

    def handle(self, *args, **options):
        """primary functionality"""
        User = get_user_model()
        user_count = User.objects.count()
        if 0 != user_count:
            if 1 == user_count:
                user_count = (
                    "There is already a user - default superuser will not be added"
                )
            else:
                user_count = f"There are {user_count} users  - default superuser will not be added"
            self.stdout.write(self.style.SUCCESS(user_count))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"No users in the database - {settings.SUPERUSER_DEFAULT_NAME} / {settings.SUPERUSER_DEFAULT_EMAIL} will be created as a super user."
                )
            )
            User.objects.create_superuser(
                settings.SUPERUSER_DEFAULT_NAME,
                settings.SUPERUSER_DEFAULT_EMAIL,
                settings.SUPERUSER_DEFAULT_PASSWORD,
            )

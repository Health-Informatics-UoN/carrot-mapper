"""Command to create a default superuser if no users exist"""

import django.conf as dc
from django.core.management.base import BaseCommand
import django
import os


class Command(BaseCommand):
    """Create a default superuser if no users exist"""

    help = "Create a default superuser if no users exist"

    from django.contrib.auth import get_user_model

    """wraps getUserModel so i can replace it for unit tests"""
    users = get_user_model()

    """wraps settings for unit tests"""
    settings = dc.settings

    def handle(self, *args, **options):
        """primary functionality"""

        user_count = self.users.objects.count()
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
                    f"No users in the database - {self.settings.SUPERUSER_DEFAULT_NAME} / {self.settings.SUPERUSER_DEFAULT_EMAIL} will be created as a super user."
                )
            )
            self.users.objects.create_superuser(
                self.settings.SUPERUSER_DEFAULT_NAME,
                self.settings.SUPERUSER_DEFAULT_EMAIL,
                self.settings.SUPERUSER_DEFAULT_PASSWORD,
            )

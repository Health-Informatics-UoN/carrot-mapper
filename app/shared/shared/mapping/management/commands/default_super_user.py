"""Command to create a default superuser if no users exist"""

import django.conf as dc
from django.core.management.base import BaseCommand
import django
import os


class Command(BaseCommand):
    """Create a default superuser if and only if no users exist"""

    help = "Create a default superuser if and only if no users exist"

    from django.contrib.auth import get_user_model

    """wraps getUserModel so i can replace it for unit tests"""
    users = get_user_model()

    """wraps settings for unit tests"""
    settings = dc.settings

    def handle(self, *args, **options):
        """primary functionality"""

        user_count = self.users.objects.count()
        if user_count > 0:
            message = (
                "There is already a user - default superuser will not be added"
                if user_count == 1
                else f"There are {user_count} users - default superuser will not be added"
            )
            self.stdout.write(self.style.SUCCESS(message))
            return
        else:
            # execute the creation command
            self.users.objects.create_superuser(
                self.settings.SUPERUSER_DEFAULT_NAME,
                self.settings.SUPERUSER_DEFAULT_EMAIL,
                self.settings.SUPERUSER_DEFAULT_PASSWORD,
            )
            # log the user's details
            self.stdout.write(
                self.style.SUCCESS(
                    f"Superuser successfully created with Username='{self.settings.SUPERUSER_DEFAULT_NAME}', Password='{self.settings.SUPERUSER_DEFAULT_PASSWORD}'"
                )
            )

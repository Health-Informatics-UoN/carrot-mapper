"""Command to create a default superuser if no users exist"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
import django
import django.conf as dc
import os


class Command(BaseCommand):
    """Create a default superuser if and only if no users exist"""

    help = "Create a default superuser if and only if no users exist"


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
            self.stdout.write(self.style.WARNING(message))
            return
        else:
            # execute the creation command
            self.users.objects.create_superuser(
                self.settings.SUPERUSER_DEFAULT_USERNAME,
                self.settings.SUPERUSER_DEFAULT_EMAIL,
                self.settings.SUPERUSER_DEFAULT_PASSWORD,
            )
            # log the user's details
            logged_password = self.settings.SUPERUSER_DEFAULT_PASSWORD
            logged_password = (
                logged_password[0]
                + ("*" * len(logged_password[1:-1]))
                + logged_password[-1]
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Superuser successfully created with Username='{self.settings.SUPERUSER_DEFAULT_USERNAME}', Password='{logged_password}'"
                )
            )

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
                "There is already a user - a default superuser will not be added"
                if user_count == 1
                else f"There are {user_count} users - a default superuser will not be added"
            )
            self.stdout.write(self.style.SUCCESS(message))
            return

        # https://github.com/Health-Informatics-UoN/carrot-mapper/issues/946
        su_username = self.settings.SUPERUSER_DEFAULT_USERNAME
        su_password = self.settings.SUPERUSER_DEFAULT_PASSWORD
        su_email_address = self.settings.SUPERUSER_DEFAULT_EMAIL

        # check to see if the username and password are available
        if None == su_username or None == su_password:
            if None != su_password:
                message = "no SUPERUSER_DEFAULT_USERNAME value was defined in the environment variables"
            elif None != su_username:
                message = "no SUPERUSER_DEFAULT_PASSWORD value was defined in the environment variables"
            else:
                message = "neither SUPERUSER_DEFAULT_USERNAME or SUPERUSER_DEFAULT_PASSWORD values were defined in the environment variables"


            self.stdout.write(self.style.ERROR(message))
            self.stdout.write(self.style.ERROR("no user account exists in the system"))
            return

        # execute the creation command
        self.users.objects.create_superuser(
            su_username,
            su_email_address,
            su_password,
        )
        # log the user's details
        logged_password = su_password
        logged_password = (
            logged_password[0]
            + ("*" * len(logged_password[1:-1]))
            + logged_password[-1]
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Superuser created with Username='{su_username}', Password='{logged_password}'"
            )
        )

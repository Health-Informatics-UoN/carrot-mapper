import os
import django
from django.conf import settings
from django.contrib.auth import get_user_model

def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    User = get_user_model()
    user_count = User.objects.count()
    if 0 != user_count:
        print(f"There are {user_count} users so no default user will be created.")
    else:
        print(f"There are no users so user {settings.SUPERUSER_DEFAULT_NAME} will be created as a super user.")
        User.objects.create_superuser(
            settings.SUPERUSER_DEFAULT_NAME,
            settings.SUPERUSER_DEFAULT_EMAIL,
            settings.SUPERUSER_DEFAULT_PASSWORD
        )

    
if __name__ == "__main__":
    main()
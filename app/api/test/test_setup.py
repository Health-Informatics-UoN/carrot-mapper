import mapping.management.commands.default_super_user as dsu
from django.test import TestCase


def mocks(command):
    """rewires the mock command to point at mock objects, and, returns the lists used for mock messages and mock accounts"""

    class m_objects:
        users = []

        def count(self):
            return len(self.users)

        def create_superuser(self, name, email, password):
            self.users.append(
                {
                    "super": True,
                    "name": name,
                    "email": email,
                    "password": password,
                }
            )

    class m_users:
        objects = m_objects()

    class m_stdout:
        messages = []

        def write(self, message):
            self.messages.append(message)

    class m_style:
        def WARNING(self, message):
            return "> " + message

        def SUCCESS(self, message):
            return "; " + message

        def ERROR(self, message):
            return "! " + message

    class m_settings:
        SUPERUSER_DEFAULT_USERNAME = "#name"
        SUPERUSER_DEFAULT_EMAIL = "#email"
        SUPERUSER_DEFAULT_PASSWORD = "#password"

    command.users = m_users()
    command.style = m_style()
    command.stdout = m_stdout()
    command.settings = m_settings()

    return [command.users.objects.users, command.stdout.messages]


class TestSetup(TestCase):
    """test details of setup"""

    def test_no_accounts(self):
        """tests if a (mock) account is added when the (mock) database has one"""

        command = dsu.Command()

        [users, messages] = mocks(command)

        command.handle()

        self.assertEqual(
            [
                {
                    "super": True,
                    "name": "#name",
                    "email": "#email",
                    "password": "#password",
                }
            ],
            users,
        )
        self.assertEqual(
            ["; Superuser created with Username='#name', Password='#*******d'"],
            messages,
        )

    def test_no_create_when_single_user_present(self):
        """creates a mock setup with a single user to be sure accounts won't be added in this case"""

        command = dsu.Command()

        [users, messages] = mocks(command)

        geo = {
            "super": False,
            "name": "fred",
            "email": "jake@foo",
            "password": "ieatbugs",
        }
        users.append(geo)

        command.handle()

        self.assertEqual([geo], users)
        self.assertEqual(
            ["; There is already a user - a default superuser will not be added"],
            messages,
        )

    def test_entrypoint(self):
        """tests to see if there's a line in the entrypoint.sh to trigger the command"""
        import os

        found = False

        entry = __file__
        entry = os.path.dirname(entry)
        entry = os.path.dirname(entry)
        entry = os.path.join(entry, "entrypoint.sh")

        with open(entry, "r") as file:
            for line in file.read().splitlines():
                line = line.strip()
                print(line)
                if "python manage.py default_super_user" == line:
                    self.assertFalse(found)
                    found = True
        self.assertTrue(found)

    def test_multiple_accounts_already(self):
        """creates a mock setup with three users to be sure accounts won't be added in this case"""

        command = dsu.Command()

        [users, messages] = mocks(command)

        account = {
            "super": False,
            "name": "fred",
            "email": "jake@foo",
            "password": "ieatbugs",
        }
        users.append(account)
        account = {
            "super": True,
            "name": "kim",
            "email": "kim@foo",
            "password": "dayweekyear",
        }
        users.append(account)
        account = {
            "super": False,
            "name": "sam",
            "email": "sammy@foo",
            "password": "drivecar",
        }
        users.append(account)

        command.handle()

        self.assertEqual(3, len(users))
        self.assertEqual(
            ["; There are 3 users - a default superuser will not be added"], messages
        )

    def test_no_env_username(self):
        """test that a user won't be created when username isn't set in env"""

        command = dsu.Command()

        [users, messages] = mocks(command)

        command.settings.SUPERUSER_DEFAULT_USERNAME = None

        command.handle()

        self.assertEqual([], users)
        self.assertEqual(
            [
                "! no SUPERUSER_DEFAULT_USERNAME value was defined in the environment variables",
                "! no user account exists in the system",
            ],
            messages,
        )

    def test_no_env_password(self):
        """test that a user won't be created when password isn't set in env"""

        command = dsu.Command()

        [users, messages] = mocks(command)

        command.settings.SUPERUSER_DEFAULT_PASSWORD = None

        command.handle()

        self.assertEqual([], users)
        self.assertEqual(
            [
                "! no SUPERUSER_DEFAULT_PASSWORD value was defined in the environment variables",
                "! no user account exists in the system",
            ],
            messages,
        )

    def test_no_env_username_or_password(self):
        """test that a user won't be created when neither password or username are set in env"""

        command = dsu.Command()

        [users, messages] = mocks(command)

        command.settings.SUPERUSER_DEFAULT_USERNAME = None
        command.settings.SUPERUSER_DEFAULT_PASSWORD = None

        command.handle()

        self.assertEqual([], users)
        self.assertEqual(
            [
                "! neither SUPERUSER_DEFAULT_USERNAME or SUPERUSER_DEFAULT_PASSWORD values were defined in the environment variables",
                "! no user account exists in the system",
            ],
            messages,
        )

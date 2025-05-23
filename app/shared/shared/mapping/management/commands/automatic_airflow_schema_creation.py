import os
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):

    help = "Create Airflow schema in the database automatically"

    _SCHEMA_NAME = "airflow"
    _WORKER_SERVICE_TYPE = os.getenv("WORKER_SERVICE_TYPE")

    # Validate the schema name and worker type at class load time
    if not _SCHEMA_NAME and _WORKER_SERVICE_TYPE:
        raise ValueError("AIRFLOW_SCHEMA_NAME environment variable must be set")

    def _check_schema_exists(self):
        """
        Check if the Airflow schema already exists in the database.
        """
        try:
            # Query the information_schema to check if the schema exists
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s;",
                    [self._SCHEMA_NAME],
                )

                exists = cursor.fetchone() 
                if exists:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Schema '{self._SCHEMA_NAME}' already exists. Skipping creation."
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Schema '{self._SCHEMA_NAME}' does not exist. Proceeding to create it."
                        )
                    )

                # Return Truey if schema exists, else None
                return exists

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error checking schema existence: {str(e)}")
            )
            raise ValueError(f"Failed when checking the schema for the Airflow: {e}")

    def _create_schema(self):
        """
        Create the Airflow schema in the database.
        """

        try:
            self.stdout.write(f"Creating Airflow schema '{self._SCHEMA_NAME}'...")
            with connection.cursor() as cursor:

                # Create the schema in the PostgreSQL database 
                cursor.execute(f"CREATE SCHEMA {self._SCHEMA_NAME};")
                db_user = settings.DATABASES["default"]["USER"]
                cursor.execute(
                    f"GRANT ALL PRIVILEGES ON SCHEMA {self._SCHEMA_NAME} TO {db_user};"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created Airflow schema '{self._SCHEMA_NAME}'"
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creating schema '{self._SCHEMA_NAME}': {str(e)}")
            )
            raise ValueError(f"Failed when creating the schema for the Airflow: {e}")

    def handle(self, *args, **kwargs):
        """
        The main entry point for the command.
        
        This method checks if the Airflow schema exists and
        creates it if it doesn't.
        """

        # Only execute schema creation logic for Airflow worker type
        if self._WORKER_SERVICE_TYPE.lower() == "airflow":
            schema_exists = self._check_schema_exists()

            if not schema_exists:
                self._create_schema()

        else:
            self.stdout.write(
                self.style.WARNING(
                    "Automatic Schema creation is not required for this worker type."
                )
            )

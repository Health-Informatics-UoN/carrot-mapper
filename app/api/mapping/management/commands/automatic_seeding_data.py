from django.core.management.base import BaseCommand
from django.core.management import call_command
from mapping.models import OmopTable
from shared.files.models import FileType


class Command(BaseCommand):
    help = "Set automatic seeding of data if it is not already seeded."

    class TableMappingSeedingError(Exception):
        pass

    class FileTypeSeedingError(Exception):
        pass

    def seed_omop_tables(self):
        try:
            if not OmopTable.objects.exists():
                self.stdout.write("Seeding Omop Tables...")
                call_command("loaddata", "mapping")
            else:
                self.stdout.write("Omop Tables already seeded.")
        except Exception as e:
            raise self.TableMappingSeedingError(f"Error seeding Omop Tables: {e}")

    def seed_file_types(self):
        try:
            if not FileType.objects.exists():
                self.stdout.write("Seeding File Types...")
                call_command("loaddata", "filetypes")
            else:
                self.stdout.write("File Types data is already seeded.")
        except Exception as e:
            raise self.FileTypeSeedingError(f"Error seeding File Types: {e}")

    def handle(self, *args, **options):
        self.seed_omop_tables()
        self.seed_file_types()
        self.stdout.write(self.style.SUCCESS("Automatic seeding complete."))

from django.core.management.base import BaseCommand
from mapping.models import Dataset


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "datasets",
            default=[],
            nargs="*",
            help="""(Optional) The names of the dataset(s) to add an admin.
            By default find all datasets with no admins and add the authors of the
            scan reports in the dataset.
            """,
        )

    def handle(self, *args, **options):
        """Logic for finding the first scan report of a dataset
        and setting the author as an admin.
        """

        dataset_names = options.get("datasets")

        if dataset_names:
            print(f"Finding admins for {len(dataset_names)} dataset(s)...")
            datasets = Dataset.objects.filter(admins=None, name__in=dataset_names)

        else:
            print(f"No datasets given. Finding admins for all datasets...")
            datasets = Dataset.objects.filter(admins=None)

        for ds in datasets:
            print(f"Adding admins to {ds.name}")
            authors = [
                author
                for author in ds.scan_reports.all().values_list("author", flat=True)
            ]
            ds.admins.add(*authors)

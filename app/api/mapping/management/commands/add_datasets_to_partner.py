from django.core.management.base import BaseCommand
from mapping.models import DataPartner, Dataset


class Command(BaseCommand):
    def add_arguments(self, parser):
        """Add `data_partner`, and `datasets` args."""
        parser.add_argument(
            "--data_partner",
            required=False,
            type=str,
            default="None",
            help='The data partner that owns the dataset(s). Default: "None"',
        )
        parser.add_argument(
            "datasets",
            default=[],
            nargs="*",
            help="""(Optional) The names of the dataset(s) to add to the data partner.
            By default find all datasets with no data partner and add them to the specified
            data partner or to the data partner of the dataset's first scan report.
            """,
        )

    def handle(self, *args, **options):
        """Logic for finding unpartnered Datasets
        and adding them to a Data Partner.
        """

        data_partner_name = options.get("data_partner")
        dataset_names = options.get("datasets")

        print(f"Datasets will be added to Data Partner: {data_partner_name}.")

        if dataset_names:
            # Get only the specified datasets
            print("Fetching the specified datasets...")
            orphaned_datasets = Dataset.objects.filter(name__in=dataset_names)
        else:
            # Get only the datasets with no data partner
            print("No datasets given. Fetching the unpartnered datasets...")
            orphaned_datasets = Dataset.objects.filter(data_partner=None)

        # Attach datasets to the data partner
        for dataset in orphaned_datasets:
            # Use the first scan report's data partner if it exists
            if partner_from_scanreport := dataset.scan_reports.first():
                print(
                    f"{dataset.name}'s scan reports belong to {partner_from_scanreport.data_partner.name}."
                )
                print(
                    f"Attaching {dataset.name} to Data Partner: {partner_from_scanreport.data_partner.name}."
                )
                dataset.data_partner = partner_from_scanreport.data_partner
            # Else, use the one specified in the command line
            else:
                print(f"{dataset.name} is unpartnered.")
                print(f"Attaching {dataset.name} to Data Partner: {data_partner.name}.")
                data_partner, _ = DataPartner.objects.get_or_create(
                    name=data_partner_name
                )
                dataset.data_partner = data_partner
            dataset.save()

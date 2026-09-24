import logging
from typing import List

from mapping.models import ScanReportField, ScanReportTable

from services.models import DomainMapping
from services.storage_service import StorageService

logger = logging.getLogger("test_table_mapping_logger")

storage_service = StorageService()


def get_field_domain_mappings(
    data_dictionary_blob: str, table: ScanReportTable
) -> List[DomainMapping]:
    """
    Get field-domain pair mappings for a table from the data dictionary.

    A field-domain mapping tells the auto-mapping pipeline to look up each of that
    field's source values by name (case-insensitively) within a specific OMOP domain,
    e.g. a field whose values are drug names can be mapped to the "Drug" domain.

    Args:
        data_dictionary_blob: Name of the data dictionary blob.
        table: Pre-fetched ScanReportTable instance to get mappings.
    Returns:
        List of domain mappings containing:
        - sr_field_id: Scan report field ID
        - field_data_type: The field's data type (optional)
        - domain_id: Assigned OMOP domain (optional)
    Example:
        [{
            "sr_field_id": 123,
            "field_data_type": "string",
            "domain_id": "Drug"
        }]
    """
    try:
        # STEP: 1. Get domain mappings from the DD blob
        _, _, domain_dictionary = storage_service.get_data_dictionary(
            data_dictionary_blob
        )

        # STEP: 2. Check if the table has domain mappings
        table_domains = (domain_dictionary or {}).get(table.name, {})

        if not table_domains:
            logger.info(f"No domain mappings found for table {table.name}")
            return []

        # STEP: 3. Get all fields for the table
        fields = ScanReportField.objects.filter(
            scan_report_table=table.pk, name__in=table_domains.keys()
        ).values("id", "name", "type_column")

        # STEP: 4. Build a mapping of field names to their IDs and data types
        field_info = {
            field["name"]: {"id": field["id"], "data_type": field["type_column"]}
            for field in fields
        }

        # STEP: 5. Build the output list
        output_list = [
            {
                "sr_field_id": field_info[field_name]["id"],
                "field_data_type": field_info[field_name]["data_type"],
                "domain_id": domain_id,
            }
            for field_name, domain_id in table_domains.items()
            if field_name in field_info
        ]

        logger.info(f"Domain mappings output: {output_list}")
        return output_list

    except Exception as e:
        logger.error(
            f"Error fetching domain mappings for table {table.name} (ID: {table.pk})."
            f"DD blob: {data_dictionary_blob}. Error: {e}"
        )
        raise GetFieldDomainMappingError(f"Error fetching field-domain mappings: {e}")


class GetFieldDomainMappingError(Exception):
    """Custom exception for errors in fetching field-domain mappings."""

    pass

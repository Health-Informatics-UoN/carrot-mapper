import logging
from typing import List

from shared.mapping.models import ScanReportTable, ScanReportField
from shared.services.storage_service import StorageService
from shared.services.models import VocabularyMapping

logger = logging.getLogger("test_table_mapping_logger")

storage_service = StorageService()


def get_field_vocab_mappings(
    data_dictionary_blob: str, table: ScanReportTable
) -> List[VocabularyMapping]:
    """
    Get field-vocab pair mappings for a table from the data dictionary.
    Args:
        data_dictionary_blob: Name of the data dictionary blob.
        table: Pre-fetched ScanReportTable instance to get mappings.
    Returns:
        List of vocabulary mappings containing:
        - sr_field_id: Scan report field ID
        - field_data_type: The field's data type (optional)
        - vocabulary_id: Assigned vocabulary ID (optional)
    Example:
        [{
            "sr_field_id": 123,
            "field_data_type": "string",
            "vocabulary_id": "LOINC"
        }]
    """
    try:
        # 1. Get vocabulary mappings from the DD blob
        _, vocab_dictionary = storage_service.get_data_dictionary(data_dictionary_blob)
        table_vocab = vocab_dictionary.get(table.name, {})

        if not table_vocab:
            logger.info(f"No vocabulary mappings found for table {table.name}")
            return []

        # 2. Get all fields for the table
        fields = ScanReportField.objects.filter(
            scan_report_table=table.pk, name__in=table_vocab.keys()
        ).values("id", "name", "type_column")

        # 3. Build a mapping of field names to their IDs and data types
        field_info = {
            field["name"]: {"id": field["id"], "data_type": field["type_column"]}
            for field in fields
        }

        # 4. Build the output list
        output_list = [
            {
                "sr_field_id": field_info[field_name]["id"],
                "field_data_type": field_info[field_name]["data_type"],
                "vocabulary_id": vocab_id,
            }
            for field_name, vocab_id in table_vocab.items()
            if field_name in field_info
        ]

        logger.info(f"Vocabulary mappings output: {output_list}")
        return output_list

    except Exception as e:
        logger.error(
            f"Error fetching mappings for table {table.name} (ID: {table.pk})."
            f"DD blob: {data_dictionary_blob}. Error: {e}"
        )
        raise GetFieldVocabMappingError(f"Error fetching field-vocab mappings: {e}")


class GetFieldVocabMappingError(Exception):
    """Custom exception for errors in fetching field-vocab mappings."""

    pass

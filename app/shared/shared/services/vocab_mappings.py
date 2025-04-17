import logging
from typing import List

from shared.mapping.models import ScanReportTable
from shared.services.storage_service import StorageService
from shared_code import db
from shared_code.models import VocabularyMapping

logger = logging.getLogger("test_table_mapping_logger")

storage_service = StorageService()


def get_table_vocabulary_mappings(
    data_dictionary_blob: str, table: ScanReportTable
) -> List[VocabularyMapping]:
    """
    Get vocabulary mappings for a table from the data dictionary.
    Args:
        data_dictionary_blob: Path to the data dictionary blob in storage
        table: Pre-fetched ScanReportTable instance to get mappings for
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

    Note:
        When using the func, make sure to pass the table to retrieve
        the table ID and the data dictionary blob path.
    """
    # 1. Get field data from table_values
    table_values = db.get_scan_report_values(table.pk)

    # 2. Extract field information, including data type
    field_info = {
        value["scan_report_field"]["id"]: {
            "name": value["scan_report_field"]["name"],
            "data_type": value["scan_report_field"].get("data_type"),
        }
        for value in table_values
    }

    # 3. Get vocabulary mappings from the DD blob
    _, vocab_dictionary = storage_service.get_data_dictionary(data_dictionary_blob)
    table_vocab = vocab_dictionary.get(table.name, {})

    # 4. Build the output list
    output_list = [
        {
            "sr_field_id": field_id,
            "field_data_type": field_info[field_id]["data_type"],
            "vocabulary_id": table_vocab.get(field_info[field_id]["name"]),
        }
        for field_id in field_info
        if table_vocab.get(field_info[field_id]["name"])
    ]

    logger.info(f"Vocabulary mappings output: {output_list}")
    return output_list

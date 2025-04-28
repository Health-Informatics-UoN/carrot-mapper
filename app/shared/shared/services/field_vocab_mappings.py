import logging
from typing import List, Dict
from collections import defaultdict


from shared.mapping.models import ScanReportTable, ScanReportField
from shared.services.storage_service import StorageService
from shared.services.models import VocabularyMapping

logger = logging.getLogger("test_table_mapping_logger")

storage_service = StorageService()


def _validate_data_dictionary(data_dictionary: List[Dict]) -> None:
    """
    Validate the data dictionary for multiple empty 'value' mappings.

    This function checks if there are multiple records in the
    data dictionary with the same 'csv_file_name' and
    'field_name' but empty 'value'.

    If so, it raises an InvalidDataDictionaryError
    because one field in one table can only
    receive one vocabulary ID.

    Args:
        data_dictionary (List[Dict]): A list of dictionaries
        representing the data dictionary.

    Raises:
        InvalidDataDictionaryError: If multiple records have
        the same 'csv_file_name' and 'field_name'
        with empty 'value'.

    Returns:
        None
    """
    # STEP 1: Group records by (csv_file_name, field_name)
    field_groups = defaultdict(list)

    # STEP 2: Iterate through the data dictionary and group records
    for record in data_dictionary:
        key = (record["csv_file_name"], record["field_name"])
        field_groups[key].append(record)

    # STEP 3:  Validate each group
    for (csv_file, field_name), records in field_groups.items():

        # Only check groups with >1 record
        if len(records) > 1:

            # Count records with empty 'value' (None or "")
            empty_value_count = sum(1 for record in records if not record["value"])

            # If >1 empty 'value' in the same group → ERROR
            if empty_value_count > 1:
                raise InvalidDataDictionaryError(
                    f"Found {empty_value_count} empty 'value' mappings for "
                    f"field '{field_name}' in file '{csv_file}'. "
                    "One field in one table can only receive one vocab ID."
                )


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
        # STEP: 1. Get vocabulary mappings from the DD blob
        _, vocab_dictionary = storage_service.get_data_dictionary(
            data_dictionary_blob
        )

        # STEP: 2. Validate the data dictionary
        _validate_data_dictionary(vocab_dictionary)

        # STEP: 3. Check if the table has vocabulary mappings
        table_vocab = vocab_dictionary.get(table.name, {})

        if not table_vocab:
            logger.info(f"No vocabulary mappings found for table {table.name}")
            return []

        # STEP: 4. Get all fields for the table
        fields = ScanReportField.objects.filter(
            scan_report_table=table.pk, name__in=table_vocab.keys()
        ).values("id", "name", "type_column")

        # STEP: 5. Build a mapping of field names to their IDs and data types
        field_info = {
            field["name"]: {"id": field["id"], "data_type": field["type_column"]}
            for field in fields
        }

        # STEP: 6. Build the output list
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
        return output_list, vocab_dictionary

    except Exception as e:
        logger.error(
            f"Error fetching mappings for table {table.name} (ID: {table.pk})."
            f"DD blob: {data_dictionary_blob}. Error: {e}"
        )
        raise GetFieldVocabMappingError(f"Error fetching field-vocab mappings: {e}")


class GetFieldVocabMappingError(Exception):
    """Custom exception for errors in fetching field-vocab mappings."""

    pass


class InvalidDataDictionaryError(Exception):
    """Custom exception for invalid data dictionary errors."""

    pass

from typing import Dict, Any


def clean_concept_mappings(cdm_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cleaning of concept_mappings.

    Args:
        cdm_data: The CDM data dictionary containing concept_mappings

    Returns:
        Dict[str, Any]: Cleaned CDM data dictionary
    """
    cleaned_data = cdm_data.copy()

    # Iterate through all destination tables
    for dest_table_name, dest_table_data in cleaned_data.items():
        # Iterate through all source tables
        for source_table_name, source_table_data in dest_table_data.items():
            concept_mappings = source_table_data.get("concept_mappings", {})

            # List to track concept mappings to remove
            concepts_to_remove = []

            for concept_name, concept_data in concept_mappings.items():
                original_value = concept_data.get("original_value", [])
                field_level_mapping = concept_data.get("field_level_mapping", {})
                value_level_mapping = concept_data.get("value_level_mapping", {})

                # Remove concept if all key components are empty
                if (
                    not original_value
                    and not field_level_mapping
                    and not value_level_mapping
                ):
                    concepts_to_remove.append(concept_name)
                    continue

                # Clean value_level_mapping if it exists
                if value_level_mapping and original_value:
                    values_to_remove = []

                    for value_key, field_mappings in value_level_mapping.items():
                        # Remove fields that are in original_value list
                        fields_to_remove = [
                            field_name
                            for field_name in field_mappings.keys()
                            if field_name in original_value
                        ]

                        # Remove the identified fields
                        for field_name in fields_to_remove:
                            del field_mappings[field_name]

                        # If no fields left in this value mapping, mark for removal
                        if not field_mappings:
                            values_to_remove.append(value_key)

                    # Remove empty value mappings
                    for value_key in values_to_remove:
                        del value_level_mapping[value_key]

                    # If value_level_mapping is now empty, remove it
                    if not value_level_mapping:
                        concept_data.pop("value_level_mapping", None)

                # Remove empty original_value
                if not original_value:
                    concept_data.pop("original_value", None)

                # Remove empty field_level_mapping
                if not field_level_mapping:
                    concept_data.pop("field_level_mapping", None)

                # After cleaning, check if concept is now empty
                if not concept_data:
                    concepts_to_remove.append(concept_name)

            # Remove concepts that should be removed
            for concept_name in concepts_to_remove:
                del concept_mappings[concept_name]

    return cleaned_data

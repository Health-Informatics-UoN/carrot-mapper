import os
from collections import defaultdict
from typing import Any, Dict, List, Union

from shared.services.storage_service import StorageService
from shared_code import helpers
from shared_code.logger import logger
from shared_code.models import ScanReportConceptContentType, ScanReportValueDict

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shared_code.django_settings")
import django

django.setup()

from shared.data.models import Concept, ConceptRelationship
from shared.mapping.models import ScanReportConcept, ScanReportTable
from shared_code import db
from shared_code.db import JobStageType, StageStatusType, update_job
from shared_code.helpers import ALLOWED_DOMAINS
from .reuse import reuse_existing_field_concepts, reuse_existing_value_concepts

storage_service = StorageService()


def _create_concepts(
    table_values: List[ScanReportValueDict],
) -> List[ScanReportConcept]:
    """
    Generate Concept entries ready for creating from a
    list of values.

    Only creates concepts that are in the allowed domains list AND
    have standard concept mappings (for non-standard concepts).

    Workflow:
        For each value in the table_values, checks if it is a
        valid concept or not (Yes/No).

        If Yes, check for the allowed domain and If Yes, add it
        to the final list of concepts and create the concept.

        If No for valid concept & not available in allowed
        domains, skip the concept.

        For non-standard concepts (standard_concept != "S"), skip
        if they don't have `Maps to` relationship to a standard concept.

    Args:
        - table_values (List[ScanReportValueDict]): List of
        values to create concepts from.

    Returns:
        - List[ScanReportConcept]: List of Scan Report Concepts.
    """
    concepts: List[ScanReportConcept] = []
    check_domains = True

    # Skip invalid concepts (marked with -1)
    for value in table_values:
        if value["concept_id"] == -1:
            continue

        # Making all concept_ids as a lists
        concept_ids = (
            value["concept_id"]
            if isinstance(value["concept_id"], list)
            else [value["concept_id"]]
        )

        # Track which concept IDs pass all validation checks
        valid_concept_ids = []
        for concept_id in concept_ids:
            try:
                # Verify the concept exists & in the allowed domain
                concept_obj = Concept.objects.get(concept_id=concept_id)
                if (
                    check_domains
                    and concept_obj.domain_id.lower() not in ALLOWED_DOMAINS
                ):
                    continue

                # For non-standard concepts, check if they have standard mappings
                if concept_obj.standard_concept != "S":

                    # Query the concept_relationship table
                    standard_mappings = ConceptRelationship.objects.filter(
                        concept_id_1=concept_id,
                        relationship_id="Maps to",
                        invalid_reason__isnull=True,
                    ).values_list("concept_id_2", flat=True)

                    # Skip if no standard mappings exist
                    if not standard_mappings:
                        continue

                # The valid concept ID is added to the final list
                valid_concept_ids.append(concept_id)
            except Concept.DoesNotExist:
                continue

        if not valid_concept_ids:
            continue

        # Create the concept in the final list
        for concept_id in valid_concept_ids:
            if (
                concept_instance := db.create_concept(
                    concept_id,
                    value["id"],
                    ScanReportConceptContentType.VALUE,
                )
            ) is not None:
                concepts.append(concept_instance)

    return concepts


def _transform_concepts(
    table_values: List[ScanReportValueDict], table: ScanReportTable
) -> None:
    """
    For each vocab, set "concept_id" and "standard_concept" in
    each entry in the vocab.

    Transforms the values in place.

    For the case when vocab is None, set it to defaults.

    For other cases, get the concepts from the vocab via
    /omop/conceptsfilter under pagination.

    Then match these back to the originating values, setting "concept_id" and
    "standard_concept" in each case.

    Finally, we need to fix all entries where "standard_concept" != "S"
    using `find_standard_concept_batch()`. This may result in more than
    one standard concept for a single nonstandard concept, and so
    "concept_id" may be either an int or str, or a list of such.

    Args:
        - table_values: List[ScanReportValueDict]: List of Scan Report Values.

    Returns:
        - None
    """
    # group table_values by their vocabulary_id, for example:
    # ['LOINC': [ {'id': 512, 'value': '46457-8', ... 'vocabulary_id': 'LOINC' }]],
    entries_grouped_by_vocab = defaultdict(list)
    for entry in table_values:
        entries_grouped_by_vocab[entry["vocabulary_id"]].append(entry)

    for vocab, value in entries_grouped_by_vocab.items():
        if vocab is None:
            # Set to defaults, and skip all the remaining processing that a vocab would require
            _set_defaults_for_none_vocab(value)
        else:
            _process_concepts_for_vocab(vocab, value, table)


def _set_defaults_for_none_vocab(entries: List[ScanReportValueDict]) -> None:
    """
    Set default values for entries with none vocabulary.

    Args:
        - entries (List[ScanReportValueDict]): A list of Scan
        Report Value dictionaries.

    Returns:
        - None

    """
    for entry in entries:
        entry["concept_id"] = -1
        entry["standard_concept"] = None


def _process_concepts_for_vocab(
    vocab: str, entries: List[ScanReportValueDict], table: ScanReportTable
) -> None:
    """
    Process concepts for a specific vocabulary.

    Args:
        - vocab (str): The vocabulary to process concepts for.

        - entries (List[ScanReportValueDict]): A list of Scan
        Report Value dictionaries representing the entries.

    Returns:
        - None

    """
    update_job(
        JobStageType.BUILD_CONCEPTS_FROM_DICT,
        StageStatusType.IN_PROGRESS,
        scan_report_table=table,
        details=f"Building concepts for {vocab} vocabulary",
    )
    logger.info(f"begin {vocab}")
    concept_vocab_content = _get_concepts_for_vocab(vocab, entries)

    logger.debug(
        f"Attempting to match {len(concept_vocab_content)} concepts to "
        f"{len(entries)} SRValues"
    )
    _match_concepts_to_entries(entries, concept_vocab_content)
    logger.debug("finished matching")
    _batch_process_non_standard_concepts(entries)


def _get_concepts_for_vocab(
    vocab: str, entries: List[ScanReportValueDict]
) -> List[tuple]:
    """
    Get Concepts for a specific vocabulary.

    Args:
        - vocab (str): The vocabulary to get concepts for.

        - entries (List[ScanReportValueDict]): The list of
        Scan Report Values to filter by.

    Returns:
        - List[Concept]: A list of Concepts matching the filter.

    """
    concept_codes = [entry["value"] for entry in entries]

    concepts = Concept.objects.filter(
        concept_code__in=concept_codes, vocabulary_id__iexact=vocab
    ).values_list("concept_code", "concept_id", "standard_concept")

    return list(concepts)


def _match_concepts_to_entries(
    entries: List[ScanReportValueDict], concept_vocab_content: List[tuple]
) -> None:
    """
    Match concepts to entries.

    Remarks:
        Loop over all returned concepts, and match their concept_code
        and vocabulary_id with the full_value in the entries, and
        set the latter's concept_id and standard_concept with those values

    Args:
        - entries (List[ScanReportValueDict]): A list of Scan Report Value
        dictionaries representing the entries.

        - concept_vocab_content (List[tuple]): A list of tuples
        containing (concept_code, concept_id, standard_concept).

    Returns:
        - None
    """
    # Create a mapping from concept_code to (concept_id, standard_concept)
    concept_map = {
        str(code): (concept_id, std_concept)
        for code, concept_id, std_concept in concept_vocab_content
    }

    # Set default values for all entries
    for entry in entries:
        # Look up the concept in the map, default to (-1, None) if not found
        entry["concept_id"], entry["standard_concept"] = concept_map.get(
            str(entry["value"]), (-1, None)
        )


def _batch_process_non_standard_concepts(entries: List[ScanReportValueDict]) -> None:
    """
    Batch process non-standard concepts.

    Args:
        - entries (List[ScanReportValueDict]): A list of Scan Report
        Value dictionaries representing the entries.

    Returns:
        - None
    """
    nonstandard_entries = [
        entry
        for entry in entries
        if entry["concept_id"] != -1 and entry["standard_concept"] != "S"
    ]
    logger.debug(
        f"finished selecting nonstandard concepts - selected {len(nonstandard_entries)}"
    )
    batched_standard_concepts_map = db.find_standard_concept_batch(nonstandard_entries)
    _update_entries_with_standard_concepts(entries, batched_standard_concepts_map)


def _update_entries_with_standard_concepts(
    entries: List[ScanReportValueDict], standard_concepts_map: Dict[int, Any]
) -> None:
    """
    Update entries with standard concepts.

    Remarks:
        batched_standard_concepts_map maps from an original concept
        id to a list of associated standard concepts. Use each item
        to update the relevant entry from entries[vocab].

    Args:
        - entries (List[ScanReportValueDict]): A list of Scan Report
        Value dictionaries representing the entries.

        - standard_concepts_map (Dict[str, Any]): A dictionary mapping
        non-standard concepts to standard concepts.

    Returns:
        - None

    """
    # Convert standard_concepts_map to a normal dictionary
    standard_concepts_dict = dict(standard_concepts_map)

    # Loop over all the entries
    # Convert concept_id to int to match the keys in the dictionary
    for entry in entries:
        concept_id = int(entry["concept_id"])

        # If the concept_id match the key of the dict (which is the non stantard concept),
        # update it with the value of the key (with is the standard concept)
        if concept_id in standard_concepts_dict:
            standard_concepts = standard_concepts_dict[concept_id]

            if standard_concepts:
                entry["concept_id"] = standard_concepts

            # No standard concepts found, mark as invalid
            else:
                entry["concept_id"] = -1
                entry["standard_concept"] = None


def _handle_table(
    table: ScanReportTable,
    vocab: Union[Dict[str, Dict[str, str]], None],
    trigger_reuse_concepts: bool,
) -> None:
    """
    Handles Concept Creation on a table.

    Remarks:
        Works by transforming table_values, then generating concepts from them.

    Args:
        - table (ScanReportTable): Table object to create for.
        - vocab (Dict[str, Dict[str, str]]): Vocab dictionary.

    Returns:
        - None
    """
    table_values = db.get_scan_report_values(table.pk)
    table_fields = db.get_scan_report_fields(table.pk)

    # Add vocab id to each entry from the vocab dict
    helpers.add_vocabulary_id_to_entries(table_values, vocab, table.name)

    _transform_concepts(table_values, table)
    logger.debug("finished standard concepts lookup")

    concepts = _create_concepts(table_values)

    # Bulk create Concepts
    logger.info(f"Creating {len(concepts)} concepts for table {table.name}")
    ScanReportConcept.objects.bulk_create(concepts)

    logger.info("Create concepts all finished")
    if len(concepts) == 0:
        update_job(
            JobStageType.BUILD_CONCEPTS_FROM_DICT,
            StageStatusType.COMPLETE,
            scan_report_table=table,
            details="Finished",
        )
    else:
        update_job(
            JobStageType.BUILD_CONCEPTS_FROM_DICT,
            StageStatusType.COMPLETE,
            scan_report_table=table,
            details=f"Created {len(concepts)} concepts based on provided data dictionary.",
        )
    if trigger_reuse_concepts:
        # Starting the concepts reusing process
        update_job(
            JobStageType.REUSE_CONCEPTS,
            StageStatusType.IN_PROGRESS,
            scan_report_table=table,
        )
        # handle reuse of concepts at field level
        reuse_existing_field_concepts(table_fields, table)
        update_job(
            JobStageType.REUSE_CONCEPTS,
            StageStatusType.IN_PROGRESS,
            scan_report_table=table,
            details="Finished at field level. Continuing at value level...",
        )
        # handle reuse of concepts at value level
        reuse_existing_value_concepts(table_values, table)
        update_job(
            JobStageType.REUSE_CONCEPTS,
            StageStatusType.COMPLETE,
            scan_report_table=table,
            details="Finished",
        )
    else:
        update_job(
            JobStageType.REUSE_CONCEPTS,
            StageStatusType.COMPLETE,
            scan_report_table=table,
            details="Skipped creating R (Reused) concepts because of user's preference",
        )


def main(msg: Dict[str, str]):
    """
    Processes a queue message.
    Unwraps the message content
    Gets the vocab_dictionary
    Runs the create concepts processes.

    Args:
        - msg (Dict[str, str]): The message received from the orchestrator.
    """
    data_dictionary_blob = msg.pop("data_dictionary_blob")
    table_id = msg.pop("table_id")
    trigger_reuse_concepts = msg.pop("trigger_reuse_concepts")

    # get the table
    table = ScanReportTable.objects.get(pk=table_id)

    # get the vocab dictionary
    _, vocab_dictionary = storage_service.get_data_dictionary(data_dictionary_blob)

    _handle_table(table, vocab_dictionary, trigger_reuse_concepts)

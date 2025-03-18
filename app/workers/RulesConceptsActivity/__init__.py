import os
from collections import defaultdict
from typing import Any, Dict, List, Union

from shared_code import storage_router
from shared_code import helpers
from shared_code.logger import logger
from shared_code.models import ScanReportConceptContentType, ScanReportValueDict

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shared_code.django_settings")
import django

django.setup()

from shared.data.models import Concept
from shared.mapping.models import ScanReportConcept, ScanReportTable
from shared_code import db
from shared_code.db import (
    update_job,
    JobStageType,
    StageStatusType,
)
from .reuse import reuse_existing_field_concepts, reuse_existing_value_concepts


storage_parser = storage_router.StorageService()


def _create_concepts(
    table_values: List[ScanReportValueDict],
) -> List[ScanReportConcept]:
    """
    Generate Concept entries ready for creating from a list of values.

    Args:
        - table_values (List[ScanReportValueDict]): List of values to create concepts from.

    Returns:
        - List[ScanReportConcept]: List of Scan Report Concepts.
    """
    concepts: List[ScanReportConcept] = []
    for concept in table_values:
        if concept["concept_id"] != -1:
            if isinstance(concept["concept_id"], list):
                for concept_id in concept["concept_id"]:
                    concept_instance = db.create_concept(
                        concept_id, concept["id"], ScanReportConceptContentType.VALUE
                    )
                    if concept_instance is not None:
                        concepts.append(concept_instance)
            else:
                if (
                    concept_instance := db.create_concept(
                        concept["concept_id"],
                        concept["id"],
                        ScanReportConceptContentType.VALUE,
                    )
                ) is not None:
                    concepts.append(concept_instance)

    return concepts


def _transform_concepts(
    table_values: List[ScanReportValueDict], table: ScanReportTable
) -> None:
    """
    For each vocab, set "concept_id" and "standard_concept" in each entry in the vocab.
    Transforms the values in place.

    For the case when vocab is None, set it to defaults.

    For other cases, get the concepts from the vocab via /omop/conceptsfilter under
    pagination.
    Then match these back to the originating values, setting "concept_id" and
    "standard_concept" in each case.
    Finally, we need to fix all entries where "standard_concept" != "S" using
    `find_standard_concept_batch()`. This may result in more than one standard
    concept for a single nonstandard concept, and so "concept_id" may be either an
    int or str, or a list of such.

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
        - entries (List[ScanReportValueDict]): A list of Scan Report Value dictionaries.

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
        - entries (List[ScanReportValueDict]): A list of Scan Report Value dictionaries representing the entries.

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
) -> List[Concept]:
    """
    Get Concepts for a specific vocabulary.

    Args:
        - vocab (str): The vocabulary to get concepts for.
        - entries (List[ScanReportValueDict]): The list of Scan Report Values to filter by.

    Returns:
        - List[Concept]: A list of Concepts matching the filter.

    """
    concept_codes = [entry["value"] for entry in entries]

    concepts = Concept.objects.filter(
        concept_code__in=concept_codes, vocabulary_id=vocab
    ).all()

    return list(concepts)


def _match_concepts_to_entries(
    entries: List[ScanReportValueDict], concept_vocab_content: List[Concept]
) -> None:
    """
    Match concepts to entries.

    Remarks:
        Loop over all returned concepts, and match their concept_code and vocabulary_id with
        the full_value in the entries, and set the latter's
        concept_id and standard_concept with those values

    Args:
        - entries (List[ScanReportValueDict]): A list of Scan Report Value dictionaries representing the entries.
        - concept_vocab_content (List[Concept]): A list of Concepts of the vocabulary content.

    Returns:
        - None

    """
    for entry in entries:
        entry["concept_id"] = -1
        entry["standard_concept"] = None
        for returned_concept in concept_vocab_content:
            if str(entry["value"]) == str(returned_concept.concept_code):
                entry["concept_id"] = str(returned_concept.concept_id)
                entry["standard_concept"] = str(returned_concept.standard_concept)
                # exit inner loop early if we find a concept for this entry
                break


def _batch_process_non_standard_concepts(entries: List[ScanReportValueDict]) -> None:
    """
    Batch process non-standard concepts.

    Args:
        - entries (List[ScanReportValueDict]): A list of Scan Report Value dictionaries representing the entries.

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
    entries: List[ScanReportValueDict], standard_concepts_map: Dict[str, Any]
) -> None:
    """
    Update entries with standard concepts.

    Remarks:
        batched_standard_concepts_map maps from an original concept id to
        a list of associated standard concepts. Use each item to update the
        relevant entry from entries[vocab].

    Args:
        - entries (List[ScanReportValueDict]): A list of Scan Report Value dictionaries representing the entries.
        - standard_concepts_map (Dict[str, Any]): A dictionary mapping non-standard concepts to standard concepts.

    Returns:
        - None

    """
    # Convert standard_concepts_map to a normal dictionary
    standard_concepts_dict = dict(standard_concepts_map)
    # Loop over all the entries
    for entry in entries:
        concept_id = int(
            entry["concept_id"]
        )  # Convert concept_id to int to match the keys in the dictionary
        # If the concept_id match the key of the dict (which is the non stantard concept), update it with the value of the key (with is the standard concept)
        if concept_id in standard_concepts_dict:
            entry["concept_id"] = standard_concepts_dict[concept_id]


def _handle_table(
    table: ScanReportTable, vocab: Union[Dict[str, Dict[str, str]], None]
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

    # get the table
    table = ScanReportTable.objects.get(pk=table_id)

    # get the vocab dictionary
    _, vocab_dictionary = storage_parser.get_data_dictionary(data_dictionary_blob)

    _handle_table(table, vocab_dictionary)

import json
import os
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import azure.functions as func
from shared_code.logger import logger


def unwrap_message(msg: func.QueueMessage) -> Tuple[str, str, str, str]:
    """
    Unwraps a queue message for further processing.

    Args:
        msg (func.QueueMessage): The message received from the queue.

    Returns:
        Tuple[str, str, str, str]: A tuple containing the extracted:
        - The blob containing the scan report.
        - The blob containing the data dictionary.
        - The ID of the scan report.
        - The ID of the scan report table.

    Raises:
        Exception: If the dequeue count of the message exceeds 1.
    """
    logger.info("Python queue trigger function processed a queue item.")
    message = _unwrap_message_body(msg)
    scan_report_blob, data_dictionary_blob, scan_report_id, table_id = _extract_details(
        message
    )
    return scan_report_blob, data_dictionary_blob, scan_report_id, table_id


def _unwrap_message_body(msg: func.QueueMessage) -> dict:
    """
    Unwraps the queue message to extract its body.

    Args:
        msg (func.QueueMessage): The message received from the queue.

    Returns:
        dict: The unwrapped message body.
    """
    message_body = msg.get_body().decode("utf-8")
    logger.info(f"message body: {message_body}")
    return json.loads(message_body)


def _extract_details(message: dict) -> Tuple[str, str, str, str]:
    """
    Extracts details from a unwrapped message.

    Args:
        message (dict): The unwrapped message body.

    Returns:
        Tuple[str, str, str, str]: A tuple containing the extracted:
        - The blob containing the scan report.
        - The blob containing the data dictionary.
        - The ID of the scan report.
        - The ID of the scan report table.
    """
    scan_report_blob = message.get("scan_report_blob", "")
    data_dictionary_blob = message.get("data_dictionary_blob", "")
    scan_report_id = message.get("scan_report_id", "")
    table_id = message.get("table_id", "")

    return scan_report_blob, data_dictionary_blob, scan_report_id, table_id


def flatten_list(arr: List[List[Any]]) -> List[Any]:
    """
    Flattens a List of Lists to a List.

    Args:
        arr: A Lists of Lists to flatten

    Returns:
        List(Any): A flattened list
    """
    return [item for sublist in arr for item in sublist]


def default_zero(value):
    """
    Helper function that returns the input, replacing anything Falsey
    (such as Nones or empty strings) with 0.0.
    """
    return round(value or 0.0, 2)


def handle_max_chars(max_chars: Optional[int] = None) -> int:
    if max_chars is None:
        max_chars_str = os.environ.get("PAGE_MAX_CHARS")
        max_chars = int(max_chars_str) if max_chars_str else 10000
    return max_chars


def perform_chunking(entries_to_post: List[Dict]) -> List[List[List[Dict]]]:
    """
    Splits a list of dictionaries into chunks.

    Args:
        entries_to_post (List[Dict]): A list of dictionaries to be chunked.

    Returns:
        List[List[Dict]]: A list of chunks, where each chunk is a list of dictionaries.

    This function splits the input list of dictionaries into smaller chunks based on the following criteria:
    - Each chunk's combined JSON representation should not exceed the specified maximum character limit (`max_chars`).
    - Each chunk should contain a maximum number of entries determined by the `chunk_size`.

    If the total JSON representation of entries in a chunk exceeds `max_chars`, the chunk is split into multiple chunks.
    The size of each chunk is capped at `chunk_size`. If the total number of entries exceeds `chunk_size`, multiple chunks are created.

    Config:
    - `max_chars`: Maximum JSON character length for each chunk. 'MAX_CHARS' environment variable.
    - `chunk_size`: Maximum entries allowed in each chunk. 'CHUNK_SIZE' environment variable.

    """
    max_chars = handle_max_chars()
    chunk_size_str = os.environ.get("CHUNK_SIZE")
    chunk_size = int(chunk_size_str) if chunk_size_str else 6

    chunked_entries_to_post = []
    this_page: List[Dict] = []
    this_chunk = []
    page_no = 0
    for entry in entries_to_post:
        # If the current page won't be overfull, add the entry to the current page
        if len(json.dumps(this_page)) + len(json.dumps(entry)) < max_chars:
            this_page.append(entry)
        # Otherwise, this page should be added to the current chunk.
        else:
            this_chunk.append(this_page)
            page_no += 1
            # Now check for a full chunk. If full, then add this chunk to the list
            # of chunks.
            if page_no % chunk_size == 0:
                # append the chunk to the list of chunks, then reset the chunk to empty
                chunked_entries_to_post.append(this_chunk)
                this_chunk = []
            # Now add the entry that would have over-filled the page.
            this_page = [entry]
    # After all entries are added, check for a half-filled page, and if present add
    # it to the list of pages
    if this_page:
        this_chunk.append(this_page)
    # Similarly, if a chunk ends up half-filled, add it to thelist of chunks
    if this_chunk:
        chunked_entries_to_post.append(this_chunk)

    return chunked_entries_to_post


def paginate(entries: List[str], max_chars: Optional[int] = None) -> List[List[str]]:
    """
    This expects a list of strings, and returns a list of lists of strings,
    where the maximum length of each list of strings, under JSONification,
    is less than max_chars.

    Args:
        entries (List[str]): List of strings to paginate.
        max_chars (Optional[int]): Max length, if not provided will be read from environment.

    Returns:
        List[List[str]]: A list of paginated entries.
    """
    max_chars = handle_max_chars(max_chars)

    paginated_entries = []
    this_page: List[str] = []
    for entry in entries:
        # If the current page won't be overfull, add the entry to the current page
        if len(json.dumps(this_page)) + len(json.dumps(entry)) < max_chars:
            this_page.append(entry)
        else:
            # Otherwise, this page should be added to the list of pages.
            paginated_entries.append(this_page)
            # Now add the entry that would have over-filled the page.
            this_page = [entry]

    # After all entries are added, check for a half-filled page, and if present add
    # it to the list of pages
    if this_page:
        paginated_entries.append(this_page)

    return paginated_entries


def create_concept(
    concept_id: str,
    object_id: str,
    content_type: Literal["scanreportfield", "scanreportvalue"],
    creation_type: Literal["V", "R"] = "V",
) -> Dict[str, Any]:
    """
    Creates a new Concept dict.

    Args:
        concept_id (str): The Id of the Concept to create.
        object_id (str): The Object Id of the Concept to create.
        content_type (Literal["scanreportfield", "scanreportvalue"]): The Content Type of the Concept.
        creation_type (Literal["R", "V"], optional): The Creation Type value of the Concept.

    Returns:
        Dict[str, Any]: A Concept as a dictionary.
    """
    return {
        "concept": concept_id,
        "object_id": object_id,
        "content_type": content_type,
        "creation_type": creation_type,
    }
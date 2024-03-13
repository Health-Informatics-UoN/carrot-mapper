import asyncio
import json
import os
from enum import Enum
from typing import Any, Dict, List, Literal, Union

import httpx
import requests
from shared_code import helpers, omop_helpers
from shared_code.logger import logger

# Code for making request to the API
# At some we want to use the DB directly, and make this file unnecessary.

# Set up ccom API Args:
API_URL = os.environ.get("APP_URL", "") + "api/"
HEADERS = {
    "Content-type": "application/json",
    "charset": "utf-8",
    "Authorization": f"Token {os.environ.get('AZ_FUNCTION_KEY')}",
}


class ScanReportStatus(Enum):
    UPLOAD_IN_PROGRESS = "UPINPRO"
    UPLOAD_COMPLETE = "UPCOMPL"
    UPLOAD_FAILED = "UPFAIL"
    PENDING = "PENDING"
    COMPLETE = "COMPLET"


def update_scan_report_status(id: str, status: ScanReportStatus) -> None:
    """
    Updates the status of a scan report.

    Args:
        id (str): The ID of the scan report.
        status (ScanReportStatus): The message received from the queue.

    Raises:
        Exception: requests.HTTPError: If the request fails.
    """
    response = requests.patch(
        url=f"{API_URL}scanreports/{id}/",
        data=json.dumps({"status": status.value}),
        headers=HEADERS,
    )
    response.raise_for_status()
    logger.info(f"Successfully set status to {status.value}")


def post_scan_report_table_entries(table_entries: List[Dict[str, str]]) -> List[str]:
    """
    Posts table entries to the API and returns the IDs generated.

    Args:
        table_entries (List[Dict[str, str]]): List of table entries to post.

    Returns:
        List[str]: A list of table IDs generated by the API.

    Raises:
        Exception: requests.HTTPError: If the request fails.
    """
    response = requests.post(
        url=f"{API_URL}scanreporttables/",
        data=json.dumps(table_entries),
        headers=HEADERS,
    )
    response.raise_for_status()
    tables_content = response.json()
    return [element["id"] for element in tables_content]


def post_scan_report_field_entries(
    field_entries_to_post: List[Dict[str, str]], scan_report_id: str
) -> List[str]:
    """
    POSTS field entries to the API and returns the responses.

    Args:
        field_entries_to_post (List[Dict[str, str]]): List of fields to create
        scan_report_id (str): Scan Report ID to attach to.

    Returns:
        List[str]: A list of responses returned by the API.

    Raises:
        Exception: requests.HTTPError: If the request fails.
    """
    paginated_field_entries_to_post = helpers.paginate(field_entries_to_post)
    fields_response_content = []

    for page in paginated_field_entries_to_post:
        response = requests.post(
            url=f"{API_URL}scanreportfields/",
            data=json.dumps(page),
            headers=HEADERS,
        )
        logger.info(
            f"FIELDS SAVE STATUS >>> {response.status_code} "
            f"{response.reason} {len(page)}"
        )

        if response.status_code != 201:
            update_scan_report_status(scan_report_id, ScanReportStatus.UPLOAD_FAILED)
        response.raise_for_status()
        fields_response_content += response.json()

    logger.info("POST fields all finished")
    return fields_response_content


def post_scan_report_concepts(concepts: List[str]) -> None:
    """
    POST Concepts to the API.

    Works by paginating the concepts first.

    Args:
        concepts (List[str]): A list of the concepts to POST

    Raises:
        Exception: requests.HTTPError: If the request fails.
    """
    paginated_concepts_to_post = helpers.paginate(concepts)
    responses = []
    concept_response_content = []
    for concepts_to_post_item in paginated_concepts_to_post:
        response = requests.post(
            url=f"{API_URL}scanreportconcepts/",
            headers=HEADERS,
            data=json.dumps(concepts_to_post_item),
        )
        response.raise_for_status()
        logger.info(
            f"CONCEPTS SAVE STATUS >>> " f"{response.status_code} " f"{response.reason}"
        )
        responses.append(response.json())
    concept_content = helpers.flatten_list(responses)

    concept_response_content += concept_content


def get_scan_report_fields(field_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Gets ScanReportFields that match any of the given Ids.

    Works by paginating the fields first.

    Args:
        field_ids (List[str]): The given Ids to get.

    Returns:
        List of ScanReportFields (List[Dict[str, Any]]) matching the Ids.

    Raises:
        Exception: requests.HTTPError: If the request fails.
    """
    paginated_existing_field_ids = helpers.paginate(
        field_ids, omop_helpers.max_chars_for_get
    )

    # for each list in paginated ids, get scanreport fields that match any of the given
    # ids (those with an associated concept)
    existing_fields = []
    for ids in paginated_existing_field_ids:
        ids_to_get = ",".join(map(str, ids))
        response = requests.get(
            url=f"{API_URL}scanreportfields/?id__in={ids_to_get}&fields=id,name",
            headers=HEADERS,
        )
        response.raise_for_status()
        existing_fields.append(response.json())
    return helpers.flatten_list(existing_fields)


def get_scan_report_fields_by_table(id: str) -> List[Dict[str, Any]]:
    """
    Retrieve scan report fields by table ID.

    Args:
        id (str): The ID of the table.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing the fields of the scan report table.

    Raises:
        requests.HTTPError: If the request fails.

    """
    response = requests.get(
        url=f"{API_URL}scanreportfields/?scan_report_table__in={id}&fields=id,name",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()


def get_scan_report_active_concepts(
    content_type: Literal["scanreportfield", "scanreportvalue"]
) -> List[Dict[str, Any]]:
    """
    Get ScanReportConcepts that have the given content_type and are
    in ScanReports that are "active".
    Active is:
    - Not hidden
    - With unhidden parent dataset
    - Marked with status "Mapping Complete"

    Args:
        content_type (Literal["scanreportfield", "scanreportvalue"]): The `django_content_type` to filter by.
        Represents `ScanReportField`, or `ScanReportValue`

    Returns:
        A list of ScanReportConcepts matching the criteria.

    Raises:
        Exception: requests.HTTPError: If the request fails.
    """
    response = requests.get(
        url=f"{API_URL}scanreportactiveconceptfilter/?content_type="
        f"{content_type}&fields=id,object_id,concept",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()


def get_scan_report_table(id: str) -> Dict[str, Any]:
    """
    Get a ScanReportTable for a given Id.

    Args:
        id (str): The Table Id to get.

    Returns:
        A ScanReportTable for the given Id.

    Raises:
        Exception: requests.HTTPError: If the request fails.
        Exception: KeyError: If the Scan Report Table for the ID is not found.
    """
    response = requests.get(url=f"{API_URL}scanreporttables/?id={id}", headers=HEADERS)
    response.raise_for_status()

    if scan_report_tables := response.json():
        return scan_report_tables[0]
    else:
        raise KeyError("ScanReportTable not found for the given ID.")


def get_scan_report_values(ids: str) -> List[Dict[str, Any]]:
    """
    Get ScanReportValues for Scan Reports.

    Args:
        ids (str): A string of Scan Report Ids to filter by.

    Returns:
        A list of ScanReportValues (List[Dict[str, Any]])

    Raises:
        Exception: requests.HTTPError: If the request fails.
    """
    response = requests.get(
        url=f"{API_URL}scanreportvalues/?id__in={ids}&fields=id,value,scan_report_field,"
        f"value_description",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()


def get_scan_report_values_filter_scan_report_table(id: str) -> List[Dict[str, Any]]:
    """
    Get Scan Report Values - filtered by Scan Report Table

    Args:
        id (str): ID of the Scan Report to filter by.

    Returns:
        A list of ScanReportValues (List[Dict[str, Any]])

    Raises:
        Exception: requests.HTTPError: If the request fails.
    """
    response = requests.get(
        url=f"{API_URL}scanreportvaluesfilterscanreporttable/?scan_report_table"
        f"={id}",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()


def get_concept_vocabs(
    vocab_ids: List[str], concept_codes: List[str]
) -> List[Dict[str, Any]]:
    """
    Get OMOP Concepts for a list of vocabulary Ids, and concept codes.

    Args:
        vocab_ids (List[str]): The list of vocab Ids to filter by.
        concept_codes (List[str]): The list of concept codes to filter by.

    Returns:
        A list of Concepts matching the criteria.

    Raises:
        Exception: requests.HTTPError: If the request fails.
    """
    response = requests.get(
        f"{API_URL}omop/conceptsfilter/?concept_code__in="
        f"{concept_codes}&vocabulary_id__in"
        f"={vocab_ids}",
        headers=HEADERS,
    )
    response.raise_for_status()
    logger.debug(
        f"CONCEPTS GET BY VOCAB STATUS >>> "
        f"{response.status_code} "
        f"{response.reason}"
    )
    return response.json()


async def post_chunks(
    chunked_data: List[List[Dict]],
    endpoint: str,
    text: str,
    table_name: str,
    scan_report_id: str,
) -> List[str]:
    """
    Post the chunked data to the specified endpoint.

    Args:
        chunked_data (List[List[Dict]]): A list of lists containing dictionaries of data to be posted.
        endpoint (str): The endpoint to which the data will be posted.
        text (str): A string representing the type of data being posted.
        table_name (str): The name of the table associated with the data.
        scan_report_id (str): The ID of the scan report.

    Returns:
        List[str]: A list of response content after posting the data.
    """
    response_content = []
    timeout = httpx.Timeout(60.0, connect=30.0)

    for chunk in chunked_data:
        async with httpx.AsyncClient(timeout=timeout) as client:
            tasks = []
            page_lengths = []
            for page in chunk:
                # POST chunked data to endpoint
                tasks.append(
                    asyncio.ensure_future(
                        client.post(
                            url=f"{API_URL}{endpoint}/",
                            data=json.dumps(page),
                            headers=HEADERS,
                        )
                    )
                )
                page_lengths.append(len(page))

            responses = await asyncio.gather(*tasks)

        for response, page_length in zip(responses, page_lengths):
            logger.info(
                f"{text.upper()} SAVE STATUSES on {table_name} >>>"
                f" {response.status_code} "
                f"{response.reason_phrase} {page_length}"
            )

            if response.status_code != 201:
                update_scan_report_status(
                    scan_report_id, ScanReportStatus.UPLOAD_FAILED
                )
                response.raise_for_status()

            response_content += response.json()
    return response_content

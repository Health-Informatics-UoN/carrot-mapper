import os
from typing import Any, Dict

import azure.durable_functions as df

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shared_code.django_settings")
import django
from shared_code.logger import logger

django.setup()

from shared.services.rules import find_existing_concepts_count


def orchestrator_function(context: df.DurableOrchestrationContext):
    """
    Orchestration.

    Remarks:
        - Call CreateConcepts
        - Get the number of existing concepts count
        - Paginate it...
        - Then fan out by giving MappingRules a page number
    """

    # CreateConcepts
    msg: Dict[str, Any] = context.get_input()
    result = yield context.call_activity("CreateConcepts", msg)

    table_id = msg.get("table_id")

    # Get concepts number
    concepts_count = find_existing_concepts_count(table_id)
    logger.info(f"Concepts found: {concepts_count}")

    # Paginate, but ensure we have at least 1 task.
    page_size = os.environ.get("PAGE_SIZE", 1000)
    num_pages = max((concepts_count + page_size - 1) // page_size, 1)

    # Fan out
    tasks = [
        context.call_activity(
            "MappingRules",
            {"table_id": table_id, "page_num": page_num, "page_size": page_size},
        )
        for page_num in range(num_pages)
    ]
    results = yield context.task_all(tasks)

    return [result, results]


main = df.Orchestrator.create(orchestrator_function)

import os
from typing import Any, Dict

import azure.durable_functions as df  # type: ignore

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shared_code.django_settings")
import django
from shared_code.logger import logger

django.setup()

from shared.services.rules import find_existing_concepts_count
from shared_code.db import (
    update_job,
    JobStageType,
    StageStatusType,
)
from shared.mapping.models import ScanReportTable
from shared.jobs.models import Job, JobStage, StageStatus


def orchestrator_function(context: df.DurableOrchestrationContext):
    """
    Orchestrates the creation of concepts and mapping rules for a given table.

    Args:
        context (DurableOrchestrationContext): The durable orchestration context.

    Returns:
        List: A list containing the result of creating concepts and the results of mapping rules.

    Raises:
        None
    """
    try:
        msg: Dict[str, Any] = context.get_input()

        # CreateConcepts
        result = yield context.call_activity("RulesConceptsActivity", msg)

        table_id = msg.pop("table_id")

        # Get concepts number
        concepts_count = find_existing_concepts_count(table_id)
        logger.info(f"Concepts found: {concepts_count}")

        # Paginate, but ensure we have at least 1 task.
        page_size = int(os.environ.get("PAGE_SIZE", "1000"))
        num_pages = max((concepts_count + page_size - 1) // page_size, 1)

        update_job(
            JobStageType.GENERATE_RULES,
            StageStatusType.IN_PROGRESS,
            scan_report_table=ScanReportTable.objects.get(id=table_id),
            details=f"Generating mapping rules from available concepts.",
        )
        # Fan out
        tasks = [
            context.call_activity(
                "RulesGenerationActivity",
                {"table_id": table_id, "page_num": page_num, "page_size": page_size},
            )
            for page_num in range(num_pages)
        ]
        results = yield context.task_all(tasks)

        update_job(
            JobStageType.GENERATE_RULES,
            StageStatusType.COMPLETE,
            scan_report_table=ScanReportTable.objects.get(id=table_id),
            details="Finished",
        )
        return [result, results]
    except Exception as e:
        logger.error(f"Orchestrator function failed: {e}")
        update_job(
            JobStageType.GENERATE_RULES,
            StageStatusType.FAILED,
            scan_report_table=ScanReportTable.objects.get(id=table_id),
            details=f"Rules Orchestrator function failed: {e}",
        )
        raise


main = df.Orchestrator.create(orchestrator_function)

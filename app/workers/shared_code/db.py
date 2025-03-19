from collections import OrderedDict, defaultdict
from typing import Any, Dict, List, Literal, Optional, Union
from enum import Enum

from django.contrib.contenttypes.models import ContentType
from django.db.models.query import QuerySet
from shared.data.models import Concept, ConceptRelationship
from shared.mapping.models import (
    ScanReport,
    ScanReportConcept,
    ScanReportField,
    ScanReportValue,
    ScanReportTable,
    UploadStatus,
)
from shared_code.logger import logger
from shared_code.models import (
    ScanReportConceptContentType,
    ScanReportFieldDict,
    ScanReportValueDict,
)
from shared.jobs.models import Job, JobStage, StageStatus


class StageStatusType(Enum):
    IN_PROGRESS = "Job in Progress"
    COMPLETE = "Job Complete"
    FAILED = "Job Failed"


class JobStageType(Enum):
    UPLOAD_SCAN_REPORT = "Upload Scan Report"
    BUILD_CONCEPTS_FROM_DICT = "Build concepts from OMOP Data dictionary"
    REUSE_CONCEPTS = "Reuse concepts from other scan reports"
    GENERATE_RULES = "Generate mapping rules from available concepts"
    DOWNLOAD_RULES = "Generate and download mapping rules JSON"


def update_job(
    stage: JobStageType,
    status: StageStatusType,
    scan_report: Optional[ScanReport] = None,
    scan_report_table: Optional[ScanReportTable] = None,
    details: Optional[str] = None,
) -> None:
    """
    Updates the stage and stage status of an existed job.
    Args:
        scan_report_id | scan_report_table_id (str): The ID of the object that need updating.
        stage (JobStageType): The stage that need status updating.
        status (StageStatusType): The status to update the Scan Report with.
        details (str): The details of the update
    Returns: None
    """
    # Get stage and status entities
    job_stage_entity = JobStage.objects.get(value=stage.name)
    stage_status_entity = StageStatus.objects.get(value=status.name)
    upload_status_entity = UploadStatus.objects.get(value=status.name)

    # Update scan report upload status if the stage is UPLOAD_SCAN_REPORT
    if scan_report and stage.name == "UPLOAD_SCAN_REPORT":
        scan_report.upload_status = upload_status_entity
        scan_report.save()
    else:
        # Get the latest job record to update based on scan_report or scan_report_table
        job = None
        if scan_report:
            job = Job.objects.filter(
                scan_report=scan_report, stage=job_stage_entity
            ).order_by("-created_at")[0]
        elif scan_report_table:
            job = Job.objects.filter(
                scan_report_table=scan_report_table, stage=job_stage_entity
            ).order_by("-created_at")[0]

        if job:
            # Update status and details
            job.status = stage_status_entity
            if details:
                job.details = details
            job.save()


def create_concept(
    concept_id: Union[str, int],
    object_id: str,
    content_type: ScanReportConceptContentType,
    creation_type: Literal["V", "R"] = "V",
) -> Optional[ScanReportConcept]:
    """
    Creates a new ScanReportConcept.

    Checks if the ScanReportConcept already exists, and returns None if it does.

    Args:
        - concept_id (str): The Id of the Concept to create.
        - object_id (str): The Object Id of the Concept to create.
        - content_type (Literal["scanreportfield", "scanreportvalue"]): The Content Type of the Concept.
        - creation_type (Literal["R", "V"], optional): The Creation Type value of the Concept.

    Returns:
        Optional[ScanReportConcept]: model.
    """
    # Check:
    content_type_model = ContentType.objects.get(model=content_type.value)
    concept_check = ScanReportConcept.objects.filter(
        concept=concept_id,
        object_id=object_id,
        content_type=content_type_model,
    ).count()

    if concept_check > 0:
        return None

    return ScanReportConcept(
        concept_id=concept_id,
        object_id=object_id,
        content_type=content_type_model,
        creation_type=creation_type,
    )


def get_scan_report_values(id: int) -> List[ScanReportValueDict]:
    """
    Get serialized Scan Report Values for a given Scan Report Table.

    Args:
        - table_id (int): The table_id to filter by.

    Returns:
        - List[ScanReportValue]: A list of serialized Scan Report Value dictionaries.

    """
    sr_values = ScanReportValue.objects.filter(
        scan_report_field__scan_report_table=id
    ).all()
    return serialize_scan_report_values(sr_values)


def get_scan_report_fields(table_id: int) -> List[ScanReportFieldDict]:
    """
    Get serialized Scan Report Fields for a given Scan Report Table.

    Args:
        - table_id (int): The table_id to filter by.

    Returns:
        - List[ScanReportFieldDict]: A list of serialized Scan Report Field dictionaries.

    """
    sr_fields = ScanReportField.objects.filter(scan_report_table=table_id).all()
    return serialize_scan_report_fields(sr_fields)


def serialize_scan_report_values(
    table_values: QuerySet[ScanReportValue],
) -> List[ScanReportValueDict]:
    """
    Serializes a list of Scan Report Values to a list of typed dictionaries.

    Args:
        - fields (QuerySet[ScanReportValue]): QuerySet of Scan Report Values to serialize.

    Returns:
        - A list of the serialized Scan Report Values into typed dictionaries.
    """
    return [
        {
            "id": value.pk,
            "scan_report_field": {
                "id": value.scan_report_field.pk,
                "name": value.scan_report_field.name,
            },
            "value": value.value,
            "frequency": value.frequency,
            "concept_id": value.conceptID,
            "value_description": value.value_description,
        }
        for value in table_values
    ]


def serialize_scan_report_fields(
    fields: QuerySet[ScanReportField],
) -> List[ScanReportFieldDict]:
    """
    Serializes a list of Scan Report Fields to a list of typed dictionaries.

    Args:
        - fields (QuerySet[ScanReportField]): QuerySet of Scan Report Fields to serialize.

    Returns:
        - A list of the serialized Scan Report Fields into typed dictionaries.
    """
    return [{"id": field.pk, "name": field.name} for field in fields]


def get_scan_report_active_concepts(
    content_type: ScanReportConceptContentType,
) -> QuerySet[ScanReportConcept]:
    """
    Gets Scan Report Concepts for the given `content_type` and in `active` SRs

    Args:
        - content_type (ScanReportConceptContentType): The content_type to filter by.

    Returns:
        - QuerySet[ScanReportConcept]: The list of Scan Report Concepts.
    """

    content_type_model = ContentType.objects.get(model=content_type.value)

    if content_type == ScanReportConceptContentType.FIELD:
        object_ids = ScanReportField.objects.filter(
            scan_report_table__scan_report__hidden=False,
            scan_report_table__scan_report__parent_dataset__hidden=False,
            scan_report_table__scan_report__mapping_status__value="COMPLETE",
        ).values_list("id", flat=True)
    elif content_type == ScanReportConceptContentType.VALUE:
        object_ids = ScanReportValue.objects.filter(
            scan_report_field__scan_report_table__scan_report__hidden=False,
            scan_report_field__scan_report_table__scan_report__mapping_status__value="COMPLETE",
        ).values_list("id", flat=True)
    else:
        raise ValueError(f"Unsupported content type: {content_type}")

    return ScanReportConcept.objects.filter(
        content_type=content_type_model, object_id__in=object_ids
    ).all()


def find_standard_concept_batch(
    source_concepts: List[ScanReportValueDict],
) -> Union[defaultdict[Any, List], Dict]:
    """
    Given a list of ScanReportValueDict, each of which contains a 'concept_id' entry,
    return a dictionary mapping from the original concept_ids to all standard
    concepts it maps to via ConceptRelationship.

    example:
    - input
      [{'id': 2575531, 'value': 'V68.0', ..., 'frequency': 2000,
        'conceptID': -1, 'vocabulary_id': 'ICD9CM', 'concept_id': '45890989',
        'standard_concept': 'None'},
       {'id': 2575530, 'value': '804.35', ..., 'frequency': 1000,
        'conceptID': -1, 'vocabulary_id': 'ICD9CM', 'concept_id': '44829331',
        'standard_concept': 'None'}
       ]

    - output
      defaultdict(<class 'list'>, {44829331: [380844, 4302223, 4307254, 42872561],
                                   45890989: [4148832]}
                  )
    """
    logger.debug("find_standard_concept_batch()")
    # Exit early rather than having to handle this case in later code.
    if not source_concepts:
        return {}

    # Get "Maps to" relations of all source concepts supplied
    concept_ids = [concept["concept_id"] for concept in source_concepts]
    concept_relationships = ConceptRelationship.objects.filter(
        relationship_id="Maps to", concept_id_1__in=concept_ids
    ).all()

    # Find those concepts with a "trail" to follow, that is, those which have
    # differing concept_id_1/2.
    filtered_concept_relations = list(
        filter(
            lambda concept_relation: concept_relation.concept_id_2
            != concept_relation.concept_id_1,
            concept_relationships,
        )
    )

    # Send all of those to conceptfilter again to check they are standard.
    concept_id_2s = [relation.concept_id_2 for relation in filtered_concept_relations]
    concepts = Concept.objects.filter(concept_id__in=concept_id_2s).all()
    concept_details = {a.concept_id: a.standard_concept for a in concepts}

    logger.debug("concepts got")

    # Filter by those concepts relationships where the second concept_id is standard
    # Now combine the pairs so that each pair is of type tuple(str, list(str))
    combined_pairs = defaultdict(list)
    for relationship in filtered_concept_relations:
        if concept_details[relationship.concept_id_2] == "S":
            combined_pairs[relationship.concept_id_1].append(relationship.concept_id_2)

    # Remove duplicates from within each entry, by converting each to an Ordered Dict
    # (the keys of which must be unique, and will preserve the order if that's
    # important) and then back to a list.
    for pair in combined_pairs:
        combined_pairs[pair] = list(OrderedDict.fromkeys(combined_pairs[pair]))

    return combined_pairs

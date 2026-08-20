from dataclasses import asdict, dataclass, field
from typing import Optional, Type

from activity_log.models import ActivityLog, ScopeType, Verb
from django.contrib.auth.models import User


@dataclass(frozen=True)
class ScanReportUploadedDetail:
    scan_report_name: str
    file_name: str


@dataclass(frozen=True)
class MappingAddedDetail:
    concept_id: int
    concept_name: str
    table_name: str
    field_name: str


@dataclass(frozen=True)
class MappingDeletedDetail:
    concept_id: int
    concept_name: str
    table_name: str
    field_name: str


@dataclass(frozen=True)
class RulesDownloadedDetail:
    file_type: str
    file_name: str


@dataclass(frozen=True)
class RulesExportRequestedDetail:
    file_type: str


@dataclass(frozen=True)
class AutomapRanDetail:
    table_id: int
    table_name: str
    trigger_reuse_concepts: bool


@dataclass(frozen=True)
class ScanReportUpdatedDetail:
    """
    Sparse by design: only the fields that actually changed are passed in,
    the rest keep their default. `record()` still enforces that only these
    keys can be present.
    """

    name_from: Optional[str] = None
    name_to: Optional[str] = None
    visibility_from: Optional[str] = None
    visibility_to: Optional[str] = None
    author_from: Optional[str] = None
    author_to: Optional[str] = None
    mapping_status_from: Optional[str] = None
    mapping_status_to: Optional[str] = None
    viewers_added: list[str] = field(default_factory=list)
    viewers_removed: list[str] = field(default_factory=list)
    editors_added: list[str] = field(default_factory=list)
    editors_removed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DatasetUpdatedDetail:
    """Sparse by design, see ScanReportUpdatedDetail."""

    name_from: Optional[str] = None
    name_to: Optional[str] = None
    visibility_from: Optional[str] = None
    visibility_to: Optional[str] = None
    admins_added: list[str] = field(default_factory=list)
    admins_removed: list[str] = field(default_factory=list)
    viewers_added: list[str] = field(default_factory=list)
    viewers_removed: list[str] = field(default_factory=list)
    editors_added: list[str] = field(default_factory=list)
    editors_removed: list[str] = field(default_factory=list)


# Every verb that carries a `detail` payload must have a matching dataclass
# here, so the shape is enforced on the write path even though the column
# itself is schemaless JSON.
_DETAIL_SCHEMAS: dict[str, Type] = {
    Verb.SCAN_REPORT_UPLOADED: ScanReportUploadedDetail,
    Verb.SCAN_REPORT_UPDATED: ScanReportUpdatedDetail,
    Verb.DATASET_UPDATED: DatasetUpdatedDetail,
    Verb.MAPPING_ADDED: MappingAddedDetail,
    Verb.MAPPING_DELETED: MappingDeletedDetail,
    Verb.RULES_EXPORT_REQUESTED: RulesExportRequestedDetail,
    Verb.RULES_DOWNLOADED: RulesDownloadedDetail,
    Verb.AUTOMAP_RAN: AutomapRanDetail,
}


def record(
    *,
    scope_type: str,
    scope_id: int,
    verb: str,
    actor: Optional[User],
    object_type: str = "",
    object_id: Optional[int] = None,
    detail: Optional[dict] = None,
) -> ActivityLog:
    """
    Create an append-only ActivityLog entry for a human-triggered event.

    `detail` is validated against the per-verb dataclass in
    `_DETAIL_SCHEMAS` before being written, so a typo or a missing field
    fails loudly at emit time rather than producing a silently malformed
    row that only breaks when something later tries to render it.
    """
    if scope_type not in ScopeType.values:
        raise ValueError(f"Unknown activity log scope_type: {scope_type!r}")
    if verb not in Verb.values:
        raise ValueError(f"Unknown activity log verb: {verb!r}")

    schema = _DETAIL_SCHEMAS.get(verb)
    if schema is not None:
        validated_detail = asdict(schema(**(detail or {})))
    elif detail:
        raise ValueError(f"Verb {verb!r} does not accept a detail payload")
    else:
        validated_detail = {}

    return ActivityLog.objects.create(
        scope_type=scope_type,
        scope_id=scope_id,
        verb=verb,
        actor=actor,
        actor_label=actor.username if actor else "",
        object_type=object_type,
        object_id=object_id,
        detail=validated_detail,
    )

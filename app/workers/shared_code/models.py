from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Literal, NotRequired, Optional, TypedDict, Union


class ScanReportConceptContentType(Enum):
    FIELD = "scanreportfield"
    VALUE = "scanreportvalue"


class ScanReportFieldDict(TypedDict):
    id: str
    name: str


class ScanReportValueDict(TypedDict):
    id: str
    scan_report_field: ScanReportFieldDict
    value: str
    frequency: int
    concept_id: Union[str, int]
    value_description: Optional[str]
    vocabulary_id: NotRequired[Optional[str]]
    standard_concept: NotRequired[Optional[str]]


class RulesFileMessage(TypedDict):
    scan_report_id: int
    user_id: str
    file_type: Literal["text/csv", "application/json", "image/svg+xml"]


@dataclass
class FileHandlerConfig:
    handler: Callable[[Any], Any]
    file_type_value: str
    file_extension: str

class VocabularyMapping(TypedDict):
    sr_field_id: int
    field_data_type: Optional[str]
    vocabulary_id: Optional[str]
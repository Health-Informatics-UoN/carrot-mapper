"""
Which OMOP fields a Scan Report Table can map at table level, by its role.

Note records aren't built from concepts alone: their text, title etc. come
from source columns, and some fields are fixed for a
whole table. These are recorded as ScanReportTableFieldMappings and exported as
the v2 rules' record-level keys (see
https://carrot.ac.uk/transform/rules_v2_notes_nlp).
"""

from dataclasses import dataclass

from mapping.models import TableRole


@dataclass(frozen=True)
class FieldSpec:
    # True if the field may take a source column / a constant value
    source: bool = True
    constant: bool = True
    required: bool = False

    @property
    def concept(self) -> bool:
        return False


@dataclass(frozen=True)
class ConceptFieldSpec(FieldSpec):
    """A *_concept_id field: only a constant, which must be a concept id"""

    source: bool = False

    @property
    def concept(self) -> bool:
        return True


# The OMOP table each role's field mappings belong to, and its mappable fields.
# note_id names the source column holding each note's key.
ROLE_OMOP_TABLE = {
    TableRole.NOTE: "note",
}

ROLE_FIELDS: dict[str, dict[str, FieldSpec]] = {
    TableRole.NOTE: {
        "note_id": FieldSpec(constant=False, required=True),
        "note_text": FieldSpec(required=True),
        "note_title": FieldSpec(),
        "note_source_value": FieldSpec(),
        "note_class_concept_id": ConceptFieldSpec(),
        "encoding_concept_id": ConceptFieldSpec(),
        "language_concept_id": ConceptFieldSpec(),
        "note_event_id": FieldSpec(constant=False),
        "note_event_field_concept_id": ConceptFieldSpec(),
    },
}

# The OMOP field holding a note's key: exported as the note table's record_key.
NOTE_KEY_FIELD = "note_id"


def allowed_fields(role: str) -> dict[str, FieldSpec]:
    return ROLE_FIELDS.get(role, {})

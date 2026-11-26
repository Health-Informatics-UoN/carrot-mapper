"""
Which OMOP fields a Scan Report Table can map at table level, by its role.

Note and note_nlp records aren't built from concepts alone: their text, title,
lexical variant etc. come from source columns, and some fields are fixed for a
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
    # True if the field may take concepts mapped from a source column's values
    values: bool = False

    @property
    def concept(self) -> bool:
        return False


@dataclass(frozen=True)
class ConceptFieldSpec(FieldSpec):
    """
    A *_concept_id field: a fixed concept, or (if `values`) concepts mapped from
    the values of a source column. Never a source column's raw values.
    """

    source: bool = False
    values: bool = True

    @property
    def concept(self) -> bool:
        return True


# The OMOP table each role's field mappings belong to, and its mappable fields.
# note_id names the source column holding a note's key: on a note table it is
# the note's own key, on a note_nlp table the key of the note it belongs to.
ROLE_OMOP_TABLE = {
    TableRole.NOTE: "note",
    TableRole.NOTE_NLP: "note_nlp",
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
        # Names the table note_event_id refers to: one fixed value per table
        "note_event_field_concept_id": ConceptFieldSpec(values=False),
    },
    TableRole.NOTE_NLP: {
        "note_id": FieldSpec(constant=False, required=True),
        "lexical_variant": FieldSpec(required=True),
        "snippet": FieldSpec(),
        "offset": FieldSpec(),
        "nlp_system": FieldSpec(),
        "section_concept_id": ConceptFieldSpec(),
        "term_exists": FieldSpec(),
        "term_temporal": FieldSpec(),
        "term_modifiers": FieldSpec(),
    },
}

# OMOP fields holding a note key: exported as a record_key on note tables and
# as a reference to the note table on note_nlp tables.
NOTE_KEY_FIELD = "note_id"


def allowed_fields(role: str) -> dict[str, FieldSpec]:
    return ROLE_FIELDS.get(role, {})


def export_problems(table) -> list[dict[str, str]]:
    """
    Why a note or note_nlp Scan Report Table would be left out of the exported
    rules (or exported without its note link), for the person mapping it. Empty
    when the table is exported in full, or has no note role.

    Each problem is {"message", "where"}, where says where it is fixed:
    "table" (Person ID / Date Event in the table settings), "fields" (the
    table's note / note_nlp fields) or "values" (concepts on a column's values).

    Mirrors the rules export: a note table needs its Person ID, Date Event and
    note_id column; a note_nlp table's record is built from the concepts mapped
    on it, so it needs at least one.
    """
    from mapping.models import MappingRule

    if table.table_role not in ROLE_OMOP_TABLE:
        return []
    is_nlp = table.table_role == TableRole.NOTE_NLP
    fields_name = "Note NLP fields" if is_nlp else "Note fields"
    problems = []
    for setting, value in (
        ("Person ID", table.person_id_id),
        ("Date Event", table.date_event_id),
    ):
        if value is None:
            problems.append(
                {
                    "message": f"{setting} isn't set. Choose its column at the top "
                    "of the table settings.",
                    "where": "table",
                }
            )
    mapped = set(table.field_mappings.values_list("omop_field__field", flat=True))
    if not mapped:
        problems.append(
            {
                "message": f"The {fields_name} haven't been saved. Choose how each "
                "is filled, then click Save fields.",
                "where": "fields",
            }
        )
    elif NOTE_KEY_FIELD not in mapped:
        key = (
            "the key of the note each term was found in"
            if is_nlp
            else "each note's key"
        )
        problems.append(
            {
                "message": f"{NOTE_KEY_FIELD} isn't set. In the {fields_name}, choose "
                f"the column holding {key}.",
                "where": "fields",
            }
        )
    if (
        is_nlp
        and not MappingRule.objects.filter(
            source_field__scan_report_table=table,
            omop_field__table__table="note_nlp",
            omop_field__field="note_nlp_concept_id",
        ).exists()
    ):
        problems.append(
            {
                "message": "No term concepts are mapped yet. This isn't one of "
                f"the {fields_name}: open the column holding each term's code "
                "(e.g. snomed_code) and map its values to concepts. Each term's "
                "note_nlp record, and any condition or other record derived from "
                "it, comes from the concept mapped to its code.",
                "where": "values",
            }
        )
    return problems

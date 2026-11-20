"""
Which OMOP fields a Scan Report Table can map at table level, by its role.

Note and note_nlp records aren't built from concepts alone: their text, title,
lexical variant etc. come from source columns, and some fields are fixed for a
whole table. These are recorded as ScanReportTableFieldMappings and exported as
the v2 rules' record-level keys (see Carrot Transform's
docs/rules_v2_record_extensions.md).
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
    # True if the field may take codes of an OMOP vocabulary from a source
    # column, for Carrot Transform to look up
    vocabulary: bool = False

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
        # The term's concept: codes of a vocabulary (looked up by Transform),
        # or concepts mapped to a column's values. Either way it also gives
        # note_nlp_source_concept_id and the records derived from the term.
        "note_nlp_concept_id": ConceptFieldSpec(
            constant=False, vocabulary=True, required=True
        ),
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

# The note_nlp field holding each term's concept. Mapping its column's values
# keeps the usual note_nlp behaviour: each concept gives a note_nlp record and
# records in its domain's table, rather than filling this one field.
TERM_CONCEPT_FIELD = "note_nlp_concept_id"


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
    required fields. A note_nlp table's term concepts come from a vocabulary's
    codes (looked up by Transform) or from concepts mapped to its term column's
    values, so with the latter it needs at least one.
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
    mappings = {
        mapping.omop_field.field: mapping
        for mapping in table.field_mappings.select_related("omop_field")
    }
    if not mappings:
        problems.append(
            {
                "message": f"The {fields_name} haven't been saved. Choose how each "
                "is filled, then click Save fields.",
                "where": "fields",
            }
        )
        return problems
    hints = {
        NOTE_KEY_FIELD: "the column holding the key of the note each term was found in"
        if is_nlp
        else "the column holding each note's key",
        TERM_CONCEPT_FIELD: "the column holding each term's code, and how its "
        "concept is found",
    }
    for name, spec in allowed_fields(table.table_role).items():
        if spec.required and name not in mappings:
            what = hints.get(name, "how it's filled")
            problems.append(
                {
                    "message": f"{name} isn't set. In the {fields_name}, choose "
                    f"{what}, then save.",
                    "where": "fields",
                }
            )
    term = mappings.get(TERM_CONCEPT_FIELD)
    if (
        is_nlp
        and term is not None
        and term.map_values
        and not MappingRule.objects.filter(
            source_field__scan_report_table=table,
            omop_field__table__table="note_nlp",
            omop_field__field=TERM_CONCEPT_FIELD,
        ).exists()
    ):
        problems.append(
            {
                "message": f"None of the values of {term.source_field.name} are "
                "mapped to concepts yet. Each term's note_nlp record, and any "
                "condition or other record derived from it, comes from the "
                "concept mapped to its value. If the column holds codes of a "
                'vocabulary such as SNOMED, choose "Codes from a vocabulary" '
                f"for {TERM_CONCEPT_FIELD} instead.",
                "where": "values",
            }
        )
    return problems

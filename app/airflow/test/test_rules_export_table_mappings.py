"""
JSON v2 export of table type concepts. See Carrot Transform's
docs/rules_v2_record_extensions.md for the format.
"""

from libs.rules_export.formats import add_table_level_mappings, rules_to_json_v2

METADATA = {"date_created": "2026-11-12T12:00:00+00:00", "dataset": "ds"}
TYPE_FIELDS = {
    "condition_occurrence": "condition_type_concept_id",
    "note": "note_type_concept_id",
}


def table(
    source_table, role, type_concept_id=None, person="patient_id", date="note_date"
):
    return {
        "source_table": source_table,
        "table_role": role,
        "type_concept_id": type_concept_id,
        "person_field": person,
        "date_field": date,
    }


def rule(
    dest_table,
    dest_field,
    concept_id=None,
    source_field="snomed_code",
    value="22298006",
):
    """One row of the temp rules table, as the driver returns it."""
    return {
        "sr_concept_id": 1,
        "source_table": "nlp.csv",
        "source_field": source_field,
        "term_mapping_value": value,
        "dest_table": dest_table,
        "dest_field": dest_field,
        "concept_id": concept_id,
        "concept_name": "Myocardial infarction",
    }


def test_standard_tables_only_get_their_type_concept():
    result = {"condition_occurrence": {"labs.csv": {"concept_mappings": {}}}}

    add_table_level_mappings(result, [table("labs.csv", "standard")], TYPE_FIELDS)

    assert result == {"condition_occurrence": {"labs.csv": {"concept_mappings": {}}}}


def test_type_concept_goes_on_every_block_of_its_table():
    result = {
        "condition_occurrence": {
            "labs.csv": {"concept_mappings": {}},
            "gp.csv": {"concept_mappings": {}},
        },
        "measurement": {"labs.csv": {"concept_mappings": {}}},
    }

    add_table_level_mappings(
        result, [table("labs.csv", "standard", type_concept_id=32817)], TYPE_FIELDS
    )

    assert result["condition_occurrence"]["labs.csv"]["constant_mappings"] == {
        "condition_type_concept_id": 32817
    }
    assert "constant_mappings" not in result["condition_occurrence"]["gp.csv"]
    # No type concept field known for measurement
    assert "constant_mappings" not in result["measurement"]["labs.csv"]


def test_json_v2_without_table_level_mappings_is_unchanged():
    rules = [rule("condition_occurrence", "condition_concept_id", 4329847)]

    assert rules_to_json_v2(rules, METADATA) == rules_to_json_v2(
        rules, METADATA, [], {}
    )

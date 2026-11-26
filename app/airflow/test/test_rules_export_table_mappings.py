"""
JSON v2 export of table roles, table-level field mappings and type concepts
(note / note_nlp support). See
https://carrot.ac.uk/transform/rules_v2_notes_nlp for the format.
"""

import json

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


def field_mapping(source_table, omop_field, source_field=None, constant_value=None):
    return {
        "source_table": source_table,
        "omop_field": omop_field,
        "source_field": source_field,
        "constant_value": constant_value,
    }


def rule(
    dest_table,
    dest_field,
    concept_id=None,
    source_field="snomed_code",
    value="22298006",
):
    """One row of the temp rules table for the NLP table, as the driver returns it."""
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


def test_note_table_becomes_a_row_block():
    result = {}

    add_table_level_mappings(
        result,
        [table("notes.csv", "note", type_concept_id=32817)],
        [
            field_mapping("notes.csv", "note_id", source_field="note_ref"),
            field_mapping("notes.csv", "note_text", source_field="text"),
            field_mapping("notes.csv", "language_concept_id", constant_value="4180186"),
            field_mapping("notes.csv", "note_title", constant_value="Letter"),
        ],
        TYPE_FIELDS,
    )

    assert result == {
        "note": {
            "notes.csv": {
                "person_id_mapping": {
                    "source_field": "patient_id",
                    "dest_field": "person_id",
                },
                "date_mapping": {
                    "source_field": "note_date",
                    "dest_field": ["note_datetime"],
                },
                "record_key": {"source_field": "note_ref"},
                "field_mappings": {"note_text": "text"},
                "constant_mappings": {
                    "language_concept_id": 4180186,
                    "note_title": "Letter",
                    "note_type_concept_id": 32817,
                },
            }
        }
    }


def test_incomplete_note_table_is_left_out():
    result = {}

    add_table_level_mappings(
        result,
        [table("notes.csv", "note", date=None)],
        [field_mapping("notes.csv", "note_id", source_field="note_ref")],
        TYPE_FIELDS,
    )

    assert result == {}


def test_note_nlp_block_gets_reference_copies_and_type():
    concept_mappings = {
        "code": {"1": {"note_nlp_concept_id": [1]}, "original_value": []}
    }
    result = {
        "note_nlp": {"nlp.csv": {"concept_mappings": concept_mappings}},
        "condition_occurrence": {"nlp.csv": {"concept_mappings": {}}},
    }

    add_table_level_mappings(
        result,
        [table("nlp.csv", "note_nlp", type_concept_id=32858)],
        [
            field_mapping("nlp.csv", "note_id", source_field="note_ref"),
            field_mapping("nlp.csv", "lexical_variant", source_field="term"),
            field_mapping("nlp.csv", "nlp_system", constant_value="MedCAT"),
        ],
        TYPE_FIELDS,
    )

    assert result["note_nlp"]["nlp.csv"] == {
        "concept_mappings": concept_mappings,
        "references": {"note_id": {"table": "note", "source_field": "note_ref"}},
        "field_mappings": {"lexical_variant": "term"},
        "constant_mappings": {"nlp_system": "MedCAT"},
    }
    # note_nlp has no type concept field; the derived conditions get it
    assert result["condition_occurrence"]["nlp.csv"]["constant_mappings"] == {
        "condition_type_concept_id": 32858
    }


def test_standard_tables_only_get_their_type_concept():
    result = {"condition_occurrence": {"labs.csv": {"concept_mappings": {}}}}

    add_table_level_mappings(result, [table("labs.csv", "standard")], [], TYPE_FIELDS)

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
        result,
        [table("labs.csv", "standard", type_concept_id=32817)],
        [],
        TYPE_FIELDS,
    )

    assert result["condition_occurrence"]["labs.csv"]["constant_mappings"] == {
        "condition_type_concept_id": 32817
    }
    assert "constant_mappings" not in result["condition_occurrence"]["gp.csv"]
    # No type concept field known for measurement
    assert "constant_mappings" not in result["measurement"]["labs.csv"]


def test_json_v2_keeps_note_nlp_concepts_without_source_value():
    rules = [
        rule("note_nlp", "note_nlp_concept_id", 4329847),
        rule("note_nlp", "note_nlp_source_concept_id", 4329847),
        rule("note_nlp", "nlp_datetime", source_field="note_date", value=None),
    ]

    cdm = json.loads(
        rules_to_json_v2(
            rules,
            METADATA,
            [table("nlp.csv", "note_nlp")],
            NLP_REQUIRED,
            TYPE_FIELDS,
        )
    )["cdm"]

    block = cdm["note_nlp"]["nlp.csv"]
    assert block["concept_mappings"]["snomed_code"]["22298006"] == {
        "note_nlp_concept_id": [4329847],
        "note_nlp_source_concept_id": [4329847],
    }
    assert block["date_mapping"] == {
        "source_field": "note_date",
        "dest_field": ["nlp_datetime"],
    }
    assert block["references"] == {
        "note_id": {"table": "note", "source_field": "note_ref"}
    }
    assert "person_id_mapping" not in block


def test_json_v2_without_table_level_mappings_is_unchanged():
    rules = [rule("condition_occurrence", "condition_concept_id", 4329847)]

    assert rules_to_json_v2(rules, METADATA) == rules_to_json_v2(
        rules, METADATA, [], [], {}
    )


def nlp_table(**link):
    return {
        **table("nlp.csv", "note_nlp", type_concept_id=32858),
        "source_domain_concept_id": None,
        "relationship_concept_id": None,
        "reverse_relationship_concept_id": None,
        **link,
    }


# What a Note NLP table needs mapped to be exported
NLP_REQUIRED = [
    field_mapping("nlp.csv", "note_id", source_field="note_ref"),
    field_mapping("nlp.csv", "lexical_variant", source_field="term"),
]

LINK = {
    "source_domain_concept_id": 905085,
    "relationship_concept_id": 900101,
    "reverse_relationship_concept_id": 900102,
}


def nlp_result():
    concept_mappings = {
        "code": {"1": {"note_nlp_concept_id": [1]}, "original_value": []}
    }
    return {
        "note_nlp": {"nlp.csv": {"concept_mappings": concept_mappings}},
        "condition_occurrence": {"nlp.csv": {"concept_mappings": {}}},
        "measurement": {"nlp.csv": {"concept_mappings": {}}},
        "condition_occurrence_other": {"labs.csv": {"concept_mappings": {}}},
    }


def test_derived_blocks_are_gated_on_note_nlp():
    result = nlp_result()

    add_table_level_mappings(result, [nlp_table()], NLP_REQUIRED, TYPE_FIELDS)

    assert result["condition_occurrence"]["nlp.csv"]["derived_from"] == {
        "table": "note_nlp"
    }
    assert result["measurement"]["nlp.csv"]["derived_from"] == {"table": "note_nlp"}
    assert "derived_from" not in result["note_nlp"]["nlp.csv"]
    assert "derived_from" not in result["condition_occurrence_other"]["labs.csv"]


def test_derived_blocks_get_exclusions_and_links():
    result = nlp_result()

    add_table_level_mappings(
        result,
        [nlp_table(**LINK)],
        NLP_REQUIRED,
        TYPE_FIELDS,
        nlp_exclusions=[
            {
                "source_table": "nlp.csv",
                "source_field": "negated",
                "excluded_values": ["true", "1"],
            },
            {
                "source_table": "other.csv",
                "source_field": "x",
                "excluded_values": ["y"],
            },
        ],
        domain_concepts={"condition_occurrence": 900019},
    )

    assert result["condition_occurrence"]["nlp.csv"]["derived_from"] == {
        "table": "note_nlp",
        "exclude_values": {"negated": ["true", "1"]},
        "fact_relationship": {
            "domain_concept_id": 900019,
            "source_domain_concept_id": 905085,
            "relationship_concept_id": 900101,
            "reverse_relationship_concept_id": 900102,
        },
    }
    # No domain concept for measurement in the vocabulary: gated, not linked
    assert result["measurement"]["nlp.csv"]["derived_from"] == {
        "table": "note_nlp",
        "exclude_values": {"negated": ["true", "1"]},
    }


def test_json_v2_passes_nlp_settings_through():
    rules = [
        rule("note_nlp", "note_nlp_concept_id", 4329847),
        rule("condition_occurrence", "condition_concept_id", 4329847),
        rule("condition_occurrence", "condition_source_value"),
        rule(
            "condition_occurrence", "person_id", source_field="patient_id", value=None
        ),
    ]

    cdm = json.loads(
        rules_to_json_v2(
            rules,
            METADATA,
            [nlp_table(**LINK)],
            NLP_REQUIRED,
            TYPE_FIELDS,
            [
                {
                    "source_table": "nlp.csv",
                    "source_field": "negated",
                    "excluded_values": ["true"],
                }
            ],
            {"condition_occurrence": 900019},
        )
    )["cdm"]

    derived = cdm["condition_occurrence"]["nlp.csv"]["derived_from"]
    assert derived["exclude_values"] == {"negated": ["true"]}
    assert derived["fact_relationship"]["domain_concept_id"] == 900019


def test_note_nlp_table_without_required_mappings_is_left_out():
    # Concepts are mapped, but the table's note_id / lexical_variant columns
    # aren't: its note_nlp records couldn't be written or linked, and its
    # derived records would lose their exclusions, so none of it is exported
    rules = [
        rule("note_nlp", "note_nlp_concept_id", 1),
        rule("condition_occurrence", "condition_concept_id", 1),
    ]
    for mappings in (
        [],
        [field_mapping("nlp.csv", "note_id", source_field="note_ref")],
        [field_mapping("nlp.csv", "lexical_variant", source_field="term")],
    ):
        output = json.loads(
            rules_to_json_v2(rules, METADATA, [nlp_table()], mappings, TYPE_FIELDS)
        )["cdm"]
        assert output == {}, mappings


def test_note_nlp_table_left_out_keeps_other_tables():
    rules = [
        rule("note_nlp", "note_nlp_concept_id", 1),
        rule("condition_occurrence", "condition_concept_id", 1),
        {
            **rule("condition_occurrence", "condition_concept_id", 2),
            "sr_concept_id": 2,
            "source_table": "gp.csv",
        },
    ]
    output = json.loads(
        rules_to_json_v2(rules, METADATA, [nlp_table()], [], TYPE_FIELDS)
    )["cdm"]
    assert list(output) == ["condition_occurrence"]
    assert list(output["condition_occurrence"]) == ["gp.csv"]

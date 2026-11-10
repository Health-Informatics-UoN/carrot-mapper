import csv
import json
from datetime import date

from libs.rules_export.formats import (
    CSV_HEADERS,
    rules_to_csv,
    rules_to_json_v1,
    rules_to_json_v2,
)

BOM = chr(0xFEFF)  # Excel-saved scan reports can leave one on the first table/field
TODAY = date(2026, 11, 10)
METADATA = {"date_created": "2026-11-10T12:00:00+00:00", "dataset": "ds"}


def rule(sr_concept_id, dest_table, dest_field, **extra):
    """One row of the temp rules table, as the database driver returns it."""
    return {
        "sr_concept_id": sr_concept_id,
        "source_table": "demographics.csv",
        "source_field": "sex",
        "term_mapping_value": None,
        "dest_table": dest_table,
        "dest_field": dest_field,
        "concept_id": None,
        "concept_name": "FEMALE",
        "creation_type": "M",
        "domain": "Gender",
        "standard_concept": "S",
        "concept_class": "Gender",
        "vocabulary": "Gender",
        "valid_start_date": date(1970, 1, 1),
        "valid_end_date": date(2099, 12, 31),
        **extra,
    }


# value mapping: sex = F -> FEMALE (8532), with its person_id and date rules
FEMALE = [
    rule(1, "person", "gender_concept_id", term_mapping_value="F", concept_id=8532),
    rule(1, "person", "gender_source_concept_id", term_mapping_value="F", concept_id=8532),
    rule(1, "person", "gender_source_value", term_mapping_value="F", concept_id=8532),
    rule(1, "person", "person_id", source_field="id", term_mapping_value="F", concept_id=8532),
    rule(1, "person", "birth_datetime", source_field="dob", term_mapping_value="F", concept_id=8532),
]  # fmt: skip
# field mapping: the whole weight field -> Body weight (3025315)
WEIGHT = [
    rule(2, "measurement", "measurement_concept_id", source_field="weight",
         concept_id=3025315, concept_name="Body weight", standard_concept=None),
    rule(2, "measurement", "measurement_source_value", source_field="weight",
         concept_id=3025315, concept_name="Body weight", standard_concept=None),
    rule(2, "measurement", "value_as_number", source_field="weight",
         concept_id=3025315, concept_name="Body weight", standard_concept=None),
    rule(2, "measurement", "person_id", source_field="id",
         concept_id=3025315, concept_name="Body weight", standard_concept=None),
]  # fmt: skip


def read_csv(text):
    return list(csv.DictReader(text.splitlines()))


# CSV


def test_csv_header():
    assert rules_to_csv([], TODAY) == ",".join(CSV_HEADERS) + "\n"


def test_csv_value_mapping():
    rows = read_csv(rules_to_csv(FEMALE, TODAY))
    assert len(rows) == len(FEMALE)  # one line per rule
    assert rows[0] == {
        "source_table": "demographics.csv",
        "source_field": "sex",
        "source_value": "F",
        "concept_id": "8532",
        "omop_term": "FEMALE",
        "class": "Gender",
        "concept": "S",
        "validity": "True",
        "domain": "Gender",
        "vocabulary": "Gender",
        "creation_type": "M",
        "rule_id": "1",
        "isFieldMapping": "0",
    }


def test_csv_concept_details_only_on_concept_id_rules():
    rows = read_csv(rules_to_csv(FEMALE, TODAY))
    person_id = rows[3]
    assert person_id["source_field"] == "id"
    assert person_id["omop_term"] == "FEMALE"
    for column in ["source_value", "concept_id", "class", "concept", "validity",
                   "vocabulary", "isFieldMapping"]:  # fmt: skip
        assert person_id[column] == ""


def test_csv_field_mapping_and_missing_values_are_blank():
    # NULL term_mapping_value / standard_concept are written blank, not "nan" / "None"
    row = read_csv(rules_to_csv(WEIGHT, TODAY))[0]
    assert row["source_value"] == ""
    assert row["concept"] == ""
    assert row["isFieldMapping"] == "1"


def test_csv_validity_uses_todays_date():
    expired = [{**FEMALE[0], "valid_end_date": TODAY}]  # end date is exclusive
    future = [{**FEMALE[0], "valid_start_date": date(2027, 1, 1)}]
    assert read_csv(rules_to_csv(expired, TODAY))[0]["validity"] == "False"
    assert read_csv(rules_to_csv(future, TODAY))[0]["validity"] == "False"


# JSON v1


def test_json_v1():
    result = json.loads(rules_to_json_v1(FEMALE + WEIGHT, METADATA))
    assert result["metadata"] == METADATA
    assert result["cdm"] == {
        "person": {
            "FEMALE 1": {
                "gender_concept_id": {
                    "source_table": "demographics.csv",
                    "source_field": "sex",
                    "term_mapping": {"F": 8532},
                },
                "gender_source_concept_id": {
                    "source_table": "demographics.csv",
                    "source_field": "sex",
                    "term_mapping": {"F": 8532},
                },
                "gender_source_value": {
                    "source_table": "demographics.csv",
                    "source_field": "sex",
                },
                "person_id": {"source_table": "demographics.csv", "source_field": "id"},
                "birth_datetime": {
                    "source_table": "demographics.csv",
                    "source_field": "dob",
                },
            }
        },
        "measurement": {
            "Body weight 2": {
                # a field mapping's term_mapping is the concept itself
                "measurement_concept_id": {
                    "source_table": "demographics.csv",
                    "source_field": "weight",
                    "term_mapping": 3025315,
                },
                "measurement_source_value": {
                    "source_table": "demographics.csv",
                    "source_field": "weight",
                },
                "value_as_number": {
                    "source_table": "demographics.csv",
                    "source_field": "weight",
                },
                "person_id": {"source_table": "demographics.csv", "source_field": "id"},
            }
        },
    }


def test_json_v1_strips_bom():
    rules = [
        {
            **FEMALE[0],
            "source_table": BOM + "demographics.csv",
            "source_field": BOM + "sex",
        }
    ]
    entry = json.loads(rules_to_json_v1(rules, METADATA))["cdm"]["person"]["FEMALE 1"]
    assert entry["gender_concept_id"]["source_table"] == "demographics.csv"
    assert entry["gender_concept_id"]["source_field"] == "sex"


# JSON v2


def test_json_v2_value_and_field_mappings():
    result = json.loads(rules_to_json_v2(FEMALE + WEIGHT, METADATA))
    assert result["metadata"] == METADATA
    # OMOP tables sorted by name
    assert list(result["cdm"]) == ["measurement", "person"]

    person = result["cdm"]["person"]["demographics.csv"]
    assert person["person_id_mapping"] == {
        "source_field": "id",
        "dest_field": "person_id",
    }
    assert person["date_mapping"] == {
        "source_field": "dob",
        "dest_field": ["birth_datetime"],
    }
    assert person["concept_mappings"] == {
        "sex": {
            "F": {"gender_concept_id": [8532], "gender_source_concept_id": [8532]},
            "original_value": ["gender_source_value"],
        }
    }

    weight = result["cdm"]["measurement"]["demographics.csv"]["concept_mappings"][
        "weight"
    ]
    assert weight["*"] == {"measurement_concept_id": [3025315]}
    # original_value comes from a set, so its order isn't fixed
    assert set(weight["original_value"]) == {
        "measurement_source_value",
        "value_as_number",
    }


def test_json_v2_mixed_mappings():
    male = [
        rule(3, "person", "gender_concept_id", term_mapping_value="M", concept_id=8507),
        rule(
            3, "person", "gender_source_value", term_mapping_value="M", concept_id=8507
        ),
    ]
    whole_field = [
        rule(4, "person", "gender_concept_id", concept_id=8551),
        rule(4, "person", "gender_source_value", concept_id=8551),
    ]
    result = json.loads(rules_to_json_v2(male + whole_field, METADATA))
    assert result["cdm"]["person"]["demographics.csv"]["concept_mappings"]["sex"] == {
        "*": {"gender_concept_id": [8551]},
        "M": {"gender_concept_id": [8507]},
        "original_value": ["gender_source_value"],
    }


def test_json_v2_groups_sorted_bom_stripped_and_null_keys_dropped():
    rules = [
        {**FEMALE[0], "source_table": "visits.csv"},
        {**FEMALE[2], "source_table": "visits.csv"},
        {
            **FEMALE[0],
            "source_table": BOM + "baseline.csv",
            "source_field": BOM + "sex",
        },
        {
            **FEMALE[2],
            "source_table": BOM + "baseline.csv",
            "source_field": BOM + "sex",
        },
        {**FEMALE[0], "source_table": None},  # no source table: left out
    ]
    person = json.loads(rules_to_json_v2(rules, METADATA))["cdm"]["person"]
    # sorted by the raw name, so the BOM-prefixed table sorts last
    assert list(person) == ["visits.csv", "baseline.csv"]
    assert list(person["baseline.csv"]["concept_mappings"]) == ["sex"]


def test_json_v2_source_field_without_source_value_is_left_out():
    # only a *_concept_id rule: no original_value, so no concept mapping
    result = json.loads(rules_to_json_v2(FEMALE[:1], METADATA))
    assert result["cdm"]["person"]["demographics.csv"] == {}

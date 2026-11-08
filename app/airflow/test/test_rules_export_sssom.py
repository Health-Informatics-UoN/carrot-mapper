import csv
from datetime import UTC, datetime

import pytest
import yaml
from libs.rules_export.sssom import build_mapping_rows, subject_id, write_sssom_tsv

CREATED = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)

# person id in field "id", date of birth in field "dob"
PERSON_FIELD = {"source_field": "id"}
DOB_FIELD = {"source_field": "dob"}


def concept_rules(
    sr_concept_id,
    concept_id,
    concept_name,
    dest_table,
    own_fields,
    *,
    source_field="sex",
    source_table="demographics.csv",
    value=None,
    date_fields=(),
    **extra,
):
    """The rules Mapper's save_mapping_rules creates for one ScanReportConcept."""
    common = {
        "sr_concept_id": sr_concept_id,
        "source_table": source_table,
        "dest_table": dest_table,
        "concept_id": concept_id,
        "concept_name": concept_name,
        "concept_domain": "Gender",
        "concept_vocabulary": "Gender",
        "vocabulary_version": "v5.0 01-OCT-26",
        "creation_type": "M",
        "confidence": None,
        "created_at": datetime(2026, 1, 2, 9, 30),
        "description": None,
        "term_mapping_value": value,
        **extra,
    }
    rules = [
        {**common, "source_field": source_field, "dest_field": f} for f in own_fields
    ]
    rules.append({**common, **PERSON_FIELD, "dest_field": "person_id"})
    rules += [{**common, **DOB_FIELD, "dest_field": f} for f in date_fields]
    return rules


GENDER_FIELDS = ["gender_concept_id", "gender_source_concept_id", "gender_source_value"]
FEMALE = concept_rules(
    7, 8532, "FEMALE", "person", GENDER_FIELDS, value="F",
    date_fields=["birth_datetime"],
)  # fmt: skip
MALE = concept_rules(
    8, 8507, "MALE", "person", GENDER_FIELDS, value="M",
    date_fields=["birth_datetime"],
    created_at=datetime(2026, 2, 3, 10, 0),
)  # fmt: skip
WEIGHT = concept_rules(
    9, 3025315, "Body weight", "measurement",
    ["measurement_concept_id", "measurement_source_concept_id", "value_as_number"],
    source_field="weight",
    concept_domain="Measurement", concept_vocabulary="LOINC",
    vocabulary_version="LOINC 2.80",
)  # fmt: skip


def parse(tsv: str):
    lines = tsv.splitlines(keepends=True)
    meta = yaml.safe_load("".join(line[1:] for line in lines if line.startswith("#")))
    table = "".join(line for line in lines if not line.startswith("#"))
    rows = list(csv.DictReader(table.splitlines(keepends=True), delimiter="\t"))
    return meta, rows


def test_one_row_per_mapped_concept():
    # three concepts, each with several rules (incl. person_id and dates)
    rows = build_mapping_rows(FEMALE + MALE + WEIGHT)
    assert [r["object_id"] for r in rows] == ["OMOP:8532", "OMOP:8507", "OMOP:3025315"]


def test_value_mapping_row():
    row = build_mapping_rows(FEMALE)[0]
    assert row["subject_id"] == "carrot:sex/F"
    assert row["subject_label"] == "F"
    assert row["predicate_id"] == "skos:exactMatch"
    assert row["object_id"] == "OMOP:8532"
    assert row["object_label"] == "FEMALE"
    assert row["object_category"] == "Gender"
    assert row["object_source"] == "omopvocab:Gender"
    assert row["object_source_version"] == "v5.0 01-OCT-26"
    assert row["mapping_justification"] == "semapv:ManualMappingCuration"
    assert row["mapping_cardinality"] == "1:1"
    assert row["mapping_date"] == "2026-01-02"


def test_field_mapping_row():
    # pandas hands back nullable int columns as floats, and NULLs as NaN
    rules = [
        {
            **r,
            "sr_concept_id": 9.0,
            "concept_id": 3025315.0,
            "term_mapping_value": float("nan"),
        }
        for r in WEIGHT
    ]
    row = build_mapping_rows(rules)[0]
    assert row["subject_id"] == "carrot:weight"
    assert row["subject_label"] == "weight"
    assert row["object_id"] == "OMOP:3025315"
    assert row["object_source"] == "omopvocab:LOINC"


@pytest.mark.parametrize(
    "field, value, expected",
    [
        ("sex", "F", "carrot:sex/F"),
        ("weight", "", "carrot:weight"),
        ("diagnosis", "breast cancer", "carrot:diagnosis/breast%20cancer"),
        # "/" only ever separates the field from the value
        ("height/weight", "1/2", "carrot:height%2Fweight/1%2F2"),
        ("code", "A01:1", "carrot:code/A01%3A1"),
    ],
)
def test_subject_ids(field, value, expected):
    assert subject_id(field, value) == expected


def test_table_is_not_part_of_the_subject():
    """The same field/value mapped to the same concept in two tables: one row."""
    other_table = concept_rules(
        17, 8532, "FEMALE", "person", GENDER_FIELDS, value="F",
        source_table="baseline.csv",
    )  # fmt: skip
    rows = build_mapping_rows(FEMALE + other_table)
    assert [(r["subject_id"], r["object_id"]) for r in rows] == [
        ("carrot:sex/F", "OMOP:8532")
    ]


def test_no_rows_for_person_id_and_date_rules():
    rows = build_mapping_rows(FEMALE)
    assert len(rows) == 1


def test_cardinality():
    # sex/F -> FEMALE only; sex/M -> MALE only: one-to-one
    # weight -> Body weight and to Body height: one subject, two objects
    # (and Body weight is only mapped from weight)
    weight_and_height = concept_rules(
        10, 3036277, "Body height", "measurement", ["measurement_concept_id"],
        source_field="weight",
    )  # fmt: skip
    # two values mapped to the same concept: many subjects, one object
    male_alias = concept_rules(
        11, 8507, "MALE", "person", ["gender_concept_id"], value="Male",
    )  # fmt: skip
    rows = build_mapping_rows(FEMALE + MALE + WEIGHT + weight_and_height + male_alias)
    assert {
        (r["subject_id"], r["object_id"]): r["mapping_cardinality"] for r in rows
    } == {
        ("carrot:sex/F", "OMOP:8532"): "1:1",
        ("carrot:sex/M", "OMOP:8507"): "n:1",
        ("carrot:sex/Male", "OMOP:8507"): "n:1",
        ("carrot:weight", "OMOP:3025315"): "1:n",
        ("carrot:weight", "OMOP:3036277"): "1:n",
    }


def test_cardinality_n_to_n():
    # sex/F -> FEMALE and MALE; sex/M -> MALE
    female_also_male = concept_rules(
        12, 8507, "MALE", "person", ["gender_concept_id"], value="F",
    )  # fmt: skip
    rows = build_mapping_rows(FEMALE + female_also_male + MALE)
    assert {
        (r["subject_id"], r["object_id"]): r["mapping_cardinality"] for r in rows
    } == {
        ("carrot:sex/F", "OMOP:8532"): "1:n",
        ("carrot:sex/F", "OMOP:8507"): "n:n",
        ("carrot:sex/M", "OMOP:8507"): "n:1",
    }


@pytest.mark.parametrize(
    "creation_type, justification",
    [
        ("M", "semapv:ManualMappingCuration"),
        ("V", "semapv:LexicalMatching"),
        ("R", "semapv:MappingChaining"),
        ("X", "semapv:LexicalMatching"),
        ("?", "semapv:UnspecifiedMatching"),
    ],
)
def test_mapping_justification(creation_type, justification):
    rules = [{**r, "creation_type": creation_type} for r in FEMALE]
    assert build_mapping_rows(rules)[0]["mapping_justification"] == justification


def test_awkward_values_are_kept_intact():
    rules = [
        {**r, "term_mapping_value": "a/b c\tdef", "description": "line one\nline two"}
        for r in FEMALE
    ]
    row = build_mapping_rows(rules)[0]
    assert row["subject_id"] == "carrot:sex/a%2Fb%20c%09def"
    # labels and comments are kept intact; the TSV writer quotes them
    assert row["subject_label"] == "a/b c\tdef"
    assert row["comment"] == "line one\nline two"


def test_missing_concept_is_an_error():
    with pytest.raises(ValueError, match="no concept_id"):
        build_mapping_rows([{**r, "concept_id": None} for r in FEMALE])


def test_full_file_metadata_and_columns():
    tsv = write_sssom_tsv(
        FEMALE + MALE + WEIGHT,
        scan_report_name="My: Dataset",
        scan_report_id=42,
        created=CREATED,
        omop_vocabulary_version="v5.0 27-FEB-25",
        mapper_version="4.3.1",
    )
    meta, rows = parse(tsv)

    # mandatory SSSOM mapping set slots
    assert meta["mapping_set_id"].endswith("/mapping-sets/scanreport/42")
    assert meta["license"]
    assert meta["mapping_set_title"] == "My: Dataset"

    # tool, dates and the OMOP release are in the metadata block
    assert meta["mapping_tool"] == "carrot-mapper"
    assert meta["mapping_tool_version"] == "4.3.1"
    assert meta["publication_date"] == "2026-11-03"
    assert meta["ext_omop_vocabulary_version"] == "v5.0 27-FEB-25"
    assert meta["object_type"] == "skos concept"  # the same for every row
    assert meta["curie_map"] == {
        "carrot": "https://carrot.ac.uk/sssom/terms/",
        "OMOP": "https://athena.ohdsi.org/search-terms/terms/",
        "omopvocab": "https://carrot.ac.uk/sssom/omop-vocabulary/",
        "carrotsssom": "https://carrot.ac.uk/sssom/",
    }
    assert meta["extension_definitions"] == [
        {
            "slot_name": "ext_omop_vocabulary_version",
            "property": "carrotsssom:ext_omop_vocabulary_version",
            "type_hint": "xsd:string",
        }
    ]

    # no extension columns
    assert list(rows[0]) == [
        "subject_id",
        "subject_label",
        "predicate_id",
        "object_id",
        "object_label",
        "object_category",
        "object_source",
        "object_source_version",
        "mapping_justification",
        "mapping_cardinality",
        "mapping_date",  # differs between rows, so stays a column
    ]
    assert [r["object_source_version"] for r in rows] == [
        "v5.0 01-OCT-26",
        "v5.0 01-OCT-26",
        "LOINC 2.80",
    ]


def test_shared_values_move_to_metadata_but_per_mapping_columns_stay():
    meta, rows = parse(write_sssom_tsv(FEMALE, "ds", 42, created=CREATED))
    # one row: everything propagatable is shared...
    assert meta["mapping_date"] == "2026-01-02"
    assert "mapping_date" not in rows[0]
    # ...but the vocabulary, its version and the cardinality stay columns
    assert "object_source_version" not in meta
    assert rows[0]["object_source"] == "omopvocab:Gender"
    assert rows[0]["object_source_version"] == "v5.0 01-OCT-26"
    assert rows[0]["mapping_cardinality"] == "1:1"


def test_optional_metadata_left_out_when_unknown():
    meta, _ = parse(write_sssom_tsv(WEIGHT, "ds", 42, created=CREATED))
    assert "ext_omop_vocabulary_version" not in meta
    assert "extension_definitions" not in meta
    assert "carrotsssom" not in meta["curie_map"]
    assert "mapping_tool_version" not in meta

"""
Parsing and full validation of SSSOM files for the registry (libs/registry_import).
Pure functions: no database or storage.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from libs.registry_import.parse import decode, parse_sssom
from libs.registry_import.validate import (
    DRAFT,
    PUBLISHED,
    STAGING_COLUMNS,
    Vocabulary,
    build_import,
    carrot_term_parts,
    normalise_license_iri,
)
from libs.rules_export.sssom import write_sssom_tsv

SPEC_DIR = Path(__file__).parent.parent / "dags" / "libs" / "sssom_spec"

VOCAB = Vocabulary(
    predicates={
        "skos:exactMatch",
        "skos:closeMatch",
        "skos:broadMatch",
        "skos:narrowMatch",
        "oboInOwl:hasDbXref",
    },
    justifications={
        "semapv:ManualMappingCuration",
        "semapv:LexicalMatching",
        "semapv:MappingChaining",
        "semapv:UnspecifiedMatching",
    },
)
# As the license_sync DAG stores them from the SPDX License List
VOCAB.add_license(
    "CC0-1.0",
    "https://spdx.org/licenses/CC0-1.0",
    ["https://creativecommons.org/publicdomain/zero/1.0/legalcode"],
)
VOCAB.add_license(
    "CC-BY-4.0",
    "https://spdx.org/licenses/CC-BY-4.0",
    ["https://creativecommons.org/licenses/by/4.0/legalcode"],
)
VOCAB.add_license(
    "LPPL-1.3c",
    "https://spdx.org/licenses/LPPL-1.3c",
    [],
    is_deprecated=True,
)

HEADER = """\
#curie_map:
#  HP: http://purl.obolibrary.org/obo/HP_
#  MP: http://purl.obolibrary.org/obo/MP_
#mapping_set_id: https://example.org/sets/hp-mp
#mapping_set_version: "1.0"
#mapping_set_title: HP to MP
#license: https://creativecommons.org/licenses/by/4.0/
"""
COLUMNS = "subject_id\tsubject_label\tpredicate_id\tobject_id\tobject_label\tmapping_justification\tconfidence\n"
ROW = "HP:0000175\tCleft palate\tskos:exactMatch\tMP:0000111\tcleft palate\tsemapv:LexicalMatching\t0.9\n"


def plan_for(text: str, overrides=None, max_issues=1000):
    return build_import(parse_sssom(text), VOCAB, overrides, max_issues=max_issues)


def codes(plan, level=None):
    return [i.code for i in plan.issues.items if level is None or i.level == level]


def row(plan, index=0) -> dict:
    return dict(zip(STAGING_COLUMNS, plan.rows[index]))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def test_parse_splits_metadata_and_rows_with_line_numbers():
    parsed = parse_sssom(HEADER + COLUMNS + ROW + ROW.replace("0.9", "0.8"))
    assert parsed.issues == []
    assert parsed.metadata["mapping_set_version"] == "1.0"
    assert parsed.header[0] == "subject_id"
    assert [line for line, _ in parsed.rows] == [9, 10]


def test_parse_reads_quoted_values_with_tabs_and_newlines():
    text = (
        HEADER
        + COLUMNS
        + 'HP:1\t"a\tb\nc ""q"""\tskos:exactMatch\tMP:1\tx\tsemapv:LexicalMatching\t\n'
        + ROW
    )
    parsed = parse_sssom(text)
    assert parsed.rows[0][1][1] == 'a\tb\nc "q"'
    # the next row starts after the quoted line break
    assert [line for line, _ in parsed.rows] == [9, 11]


def test_parse_accepts_any_consistent_space_after_hash():
    text = HEADER.replace("#", "# ") + COLUMNS + ROW
    assert parse_sssom(text).metadata["curie_map"]["HP"].endswith("HP_")


def test_parse_reports_invalid_yaml():
    parsed = parse_sssom("#curie_map: [unclosed\n" + COLUMNS + ROW)
    assert [i.code for i in parsed.issues] == ["invalid_metadata"]


def test_decode_rejects_non_utf8_and_warns_on_bom():
    text, issues = decode("﻿abc".encode())
    assert text == "abc" and [i.code for i in issues] == ["byte_order_mark"]
    text, issues = decode(b"\xff\xfe\x00")
    assert text is None and [i.code for i in issues] == ["invalid_encoding"]


# ---------------------------------------------------------------------------
# Valid files
# ---------------------------------------------------------------------------


def test_valid_file_normalises_set_and_rows():
    plan = plan_for(HEADER + COLUMNS + ROW)
    assert plan.ok, plan.issues.as_dicts()
    record = plan.mapping_set
    assert record.set_uri == "https://example.org/sets/hp-mp"
    assert record.set_version == "1.0"
    assert record.title == "HP to MP"
    assert record.license_id == "CC-BY-4.0"
    assert record.curie_map["HP"] == "http://purl.obolibrary.org/obo/HP_"
    assert plan.status == PUBLISHED

    r = row(plan)
    assert r["row_no"] == 9
    assert r["subject_iri"] == "HP:0000175" and r["subject_prefix"] == "HP"
    assert r["subject_label"] == "Cleft palate"
    assert r["object_iri"] == "MP:0000111"
    assert r["confidence"] == 0.9
    assert r["subject_ext_level"] == ""  # not a carrot subject
    assert json.loads(r["extra_metadata"]) == {}


@pytest.mark.parametrize(
    "path", sorted((SPEC_DIR / "examples").glob("*.sssom.tsv")), ids=lambda p: p.name
)
def test_official_examples_are_valid_given_a_version(path):
    plan = plan_for(path.read_text(encoding="utf-8"), {"set_version": "1"})
    assert plan.ok, plan.issues.as_dicts()
    assert plan.rows


def test_extension_slots_and_unknown_columns_go_to_extra_metadata():
    path = SPEC_DIR / "examples" / "schema" / "extension-slots.sssom.tsv"
    plan = plan_for(path.read_text(encoding="utf-8"), {"set_version": "1"})
    assert plan.ok
    assert set(codes(plan, "warning")) >= {"unknown_column", "unknown_metadata_key"}
    extra = json.loads(row(plan)["extra_metadata"])
    assert extra == {
        "ext_bar": "111",
        "ext_baz": "ORGENT:BAZ_0001",
        "ext_undeclared_baz": "BAZ A",
    }
    set_extra = plan.mapping_set.extra_metadata
    assert set_extra["ext_foo"] == "Foo A"
    assert set_extra["extension_definitions"][0]["slot_name"] == "ext_bar"


def test_carrot_export_round_trips_with_term_parts():
    rules = [
        {
            "sr_concept_id": 1,
            "source_table": "t.csv",
            "source_field": "sex",
            "term_mapping_value": "M/F",
            "dest_field": "gender_concept_id",
            "concept_id": 8507,
            "concept_name": "MALE",
            "creation_type": "M",
            "concept_domain": "Gender",
            "concept_vocabulary": "Gender",
            "vocabulary_version": "v5.0",
            "created_at": datetime(2026, 11, 3, tzinfo=UTC),
        },
        {
            "sr_concept_id": 2,
            "source_table": "t.csv",
            "source_field": "smoker",
            "term_mapping_value": None,
            "dest_field": "observation_concept_id",
            "concept_id": 4298794,
            "concept_name": "Smoker",
            "creation_type": "V",
            "created_at": datetime(2026, 11, 3, tzinfo=UTC),
        },
    ]
    text = write_sssom_tsv(
        rules,
        created=datetime(2026, 11, 4, tzinfo=UTC),
        set_metadata={
            "mapping_set_id": "https://carrot.ac.uk/registry/sets/7",
            "mapping_set_version": "2026-11-04",
            "mapping_set_title": "Scan report 7",
            "license": "https://creativecommons.org/licenses/by/4.0/",
        },
    )
    plan = plan_for(text)
    assert plan.ok, plan.issues.as_dicts()
    assert plan.issues.warnings == 0
    assert plan.mapping_set.publication_date == date(2026, 11, 4)
    assert plan.mapping_set.extra_metadata["mapping_tool"] == "carrot-mapper"

    value_row, field_row = row(plan, 0), row(plan, 1)
    assert value_row["subject_iri"] == "carrot:sex/M%2FF"
    assert (
        value_row["subject_ext_level"],
        value_row["subject_ext_field"],
        value_row["subject_ext_value"],
    ) == ("VALUE", "sex", "M/F")
    assert value_row["object_iri"] == "OMOP:8507"
    assert value_row["object_category"] == "Gender"
    assert value_row["other"] == "vocab:Gender"
    assert value_row["object_source_version"] == "v5.0"
    assert value_row["mapping_justification"] == "semapv:ManualMappingCuration"
    # mapping_date is condensed to the metadata block, and propagated back
    assert value_row["mapping_date"] == date(2026, 11, 3)
    assert (field_row["subject_ext_level"], field_row["subject_ext_field"]) == (
        "FIELD",
        "smoker",
    )
    assert field_row["mapping_justification"] == "semapv:LexicalMatching"


@pytest.mark.parametrize(
    "local, parts",
    [
        ("sex", ("FIELD", "sex", "")),
        ("sex/M", ("VALUE", "sex", "M")),
        ("a%2Fb/c%20d", ("VALUE", "a/b", "c d")),
        ("sex/", ("", "", "")),
        ("", ("", "", "")),
    ],
)
def test_carrot_term_parts(local, parts):
    assert carrot_term_parts(local) == parts


# ---------------------------------------------------------------------------
# Overrides and set-level metadata
# ---------------------------------------------------------------------------


def test_overrides_fill_gaps_and_win_with_a_warning():
    text = HEADER.replace('#mapping_set_version: "1.0"\n', "") + COLUMNS + ROW
    plan = plan_for(text)
    assert "missing_metadata_slot" in codes(plan, "error")

    plan = plan_for(text, {"set_version": "2.0", "title": "New title", "status": DRAFT})
    assert plan.ok
    assert plan.mapping_set.set_version == "2.0"
    assert plan.mapping_set.title == "New title"
    assert plan.status == DRAFT
    assert codes(plan) == ["metadata_overridden"]  # the title differed


def test_unknown_override_and_bad_status():
    plan = plan_for(HEADER + COLUMNS + ROW, {"colour": "red", "status": "LIVE"})
    assert "unknown_override" in codes(plan, "warning")
    assert "invalid_override" in codes(plan, "error")


def test_yaml_float_version_is_read_as_text_with_warning():
    plan = plan_for(HEADER.replace('"1.0"', "1.0") + COLUMNS + ROW)
    assert plan.ok
    assert plan.mapping_set.set_version == "1.0"
    assert "coerced_value" in codes(plan, "warning")


def test_unknown_license_is_a_warning_and_kept():
    other = "https://opensource.org/licenses/MIT"
    plan = plan_for(
        HEADER.replace("https://creativecommons.org/licenses/by/4.0/", other)
        + COLUMNS
        + ROW
    )
    assert plan.ok
    assert plan.mapping_set.license_id is None
    assert plan.mapping_set.extra_metadata["license"] == other
    assert "unknown_license" in codes(plan, "warning")


@pytest.mark.parametrize(
    "iri",
    [
        "https://creativecommons.org/licenses/by/4.0/",  # what SSSOM files use
        "http://creativecommons.org/licenses/by/4.0",
        "https://creativecommons.org/licenses/by/4.0/legalcode",
        "https://creativecommons.org/licenses/by/4.0/legalcode.en",
        "https://creativecommons.org/licenses/by/4.0/deed.en",
        "https://spdx.org/licenses/CC-BY-4.0",  # what the registry stores
        "https://spdx.org/licenses/CC-BY-4.0.html",
    ],
)
def test_license_matches_spdx_iri_or_see_also(iri):
    text = HEADER.replace("https://creativecommons.org/licenses/by/4.0/", iri)
    plan = plan_for(text + COLUMNS + ROW)
    assert plan.ok and codes(plan) == []
    assert plan.mapping_set.license_id == "CC-BY-4.0"


def test_license_iri_normalisation_keeps_versions_apart():
    assert normalise_license_iri(
        "https://creativecommons.org/licenses/by/4.0/"
    ) != normalise_license_iri("https://creativecommons.org/licenses/by/3.0/")
    assert normalise_license_iri("https://spdx.org/licenses/CC-BY-4.0.html") == (
        "https://spdx.org/licenses/cc-by-4.0"
    )


def test_deprecated_license_is_a_warning():
    text = HEADER.replace(
        "https://creativecommons.org/licenses/by/4.0/",
        "https://spdx.org/licenses/LPPL-1.3c",
    )
    plan = plan_for(text + COLUMNS + ROW)
    assert plan.ok
    assert plan.mapping_set.license_id == "LPPL-1.3c"
    assert codes(plan) == ["deprecated_license"]


def test_include_orcid_ids_is_a_known_override():
    plan = plan_for(HEADER + COLUMNS + ROW, {"include_orcid_ids": True})
    assert plan.ok and codes(plan) == []


def test_missing_title_falls_back_to_set_id():
    plan = plan_for(
        HEADER.replace("#mapping_set_title: HP to MP\n", "") + COLUMNS + ROW
    )
    assert plan.ok
    assert plan.mapping_set.title == "https://example.org/sets/hp-mp"
    assert "missing_title" in codes(plan, "warning")


def test_too_long_set_version_is_an_error():
    plan = plan_for(HEADER + COLUMNS + ROW, {"set_version": "v" * 101})
    assert "value_too_long" in codes(plan, "error")


# ---------------------------------------------------------------------------
# Prefixes
# ---------------------------------------------------------------------------


def test_builtin_prefix_cannot_be_redefined():
    text = HEADER.replace(
        "#curie_map:\n", "#curie_map:\n#  skos: http://example.org/skos#\n"
    )
    assert "builtin_prefix_redefined" in codes(plan_for(text + COLUMNS + ROW), "error")


def test_registry_prefix_cannot_point_elsewhere():
    text = HEADER.replace(
        "#curie_map:\n", "#curie_map:\n#  OMOP: http://example.org/omop/\n"
    )
    assert "prefix_conflict" in codes(plan_for(text + COLUMNS + ROW), "error")


def test_registry_namespace_under_another_name_is_canonicalised():
    text = HEADER.replace(
        "#curie_map:\n",
        "#curie_map:\n#  athena: https://athena.ohdsi.org/search-terms/terms/\n",
    )
    plan = plan_for(text + COLUMNS + ROW.replace("MP:0000111", "athena:8507"))
    assert plan.ok, plan.issues.as_dicts()
    assert row(plan)["object_iri"] == "OMOP:8507"
    assert row(plan)["object_prefix"] == "OMOP"


def test_undeclared_prefix_and_non_curie():
    plan = plan_for(
        HEADER
        + COLUMNS
        + ROW.replace("MP:0000111", "XX:1")
        + ROW.replace("HP:0000175", "http://x.org/1")
    )
    assert codes(plan, "error") == ["undeclared_prefix", "invalid_curie"]
    assert [i.line for i in plan.issues.items] == [9, 10]
    assert plan.rows == []


# ---------------------------------------------------------------------------
# Header and rows
# ---------------------------------------------------------------------------


def test_missing_required_column():
    text = (
        HEADER
        + COLUMNS.replace("\tmapping_justification", "")
        + ROW.replace("\tsemapv:LexicalMatching", "")
    )
    assert codes(plan_for(text), "error") == ["missing_column"]


def test_literal_mappings_are_rejected():
    path = SPEC_DIR / "examples" / "schema" / "literals.sssom.tsv"
    plan = plan_for(path.read_text(encoding="utf-8"), {"set_version": "1"})
    assert not plan.ok
    assert "missing_column" in codes(plan, "error")


@pytest.mark.parametrize(
    "old, new, code",
    [
        ("skos:exactMatch", "skos:relatedMatch", "unknown_predicate"),
        ("semapv:LexicalMatching", "semapv:MappingReview", "unknown_justification"),
        ("\t0.9\n", "\t1.5\n", "schema_violation"),
        ("\t0.9\n", "\thigh\n", "invalid_number"),
        ("HP:0000175", "", "missing_value"),
    ],
)
def test_row_errors(old, new, code):
    plan = plan_for(HEADER + COLUMNS + ROW.replace(old, new))
    assert code in codes(plan, "error")
    assert plan.issues.items[0].line == 9
    assert plan.rows == []


def test_predicate_modifier_and_cardinality_enums():
    columns = COLUMNS.replace("\n", "\tpredicate_modifier\tmapping_cardinality\n")
    good = ROW.replace("\n", "\tNot\t1:n\n")
    plan = plan_for(HEADER + columns + good)
    assert plan.ok
    assert (row(plan)["predicate_modifier"], row(plan)["mapping_cardinality"]) == (
        "Not",
        "1:n",
    )
    bad = ROW.replace("\n", "\tNOT\t2:3\n")
    plan = plan_for(HEADER + columns + bad)
    assert codes(plan, "error") == ["schema_violation", "schema_violation"]


def test_row_with_wrong_number_of_values():
    plan = plan_for(HEADER + COLUMNS + ROW.replace("\t0.9", ""))
    assert codes(plan, "error") == ["row_length"]


def test_duplicate_assertions_are_errors_but_negations_are_not():
    columns = COLUMNS.replace("\n", "\tpredicate_modifier\n")
    plain = ROW.replace("\n", "\t\n")
    negated = ROW.replace("\n", "\tNot\n")
    plan = plan_for(HEADER + columns + plain + negated + plain)
    assert codes(plan, "error") == ["duplicate_mapping"]
    assert "line 9" in plan.issues.items[0].message
    assert len(plan.rows) == 2


def test_multivalued_and_unpromoted_slots():
    columns = COLUMNS.replace("\n", "\tauthor_id\tsee_also\tsimilarity_score\n")
    data = ROW.replace(
        "\n",
        "\torcid:0000-0001-0000-0001|orcid:0000-0001-0000-0002\thttps://x.org/a\t0.5\n",
    )
    text = HEADER.replace(
        "#curie_map:\n", "#curie_map:\n#  orcid: https://orcid.org/\n"
    )
    plan = plan_for(text + columns + data)
    assert plan.ok, plan.issues.as_dicts()
    r = row(plan)
    assert json.loads(r["author_ids"]) == [
        "orcid:0000-0001-0000-0001",
        "orcid:0000-0001-0000-0002",
    ]
    assert json.loads(r["extra_metadata"]) == {
        "see_also": ["https://x.org/a"],
        "similarity_score": 0.5,
    }


def test_issues_are_capped_but_all_counted():
    rows = "".join(
        ROW.replace("skos:exactMatch", "skos:bad").replace("0000175", f"{i:07d}")
        for i in range(30)
    )
    plan = plan_for(HEADER + COLUMNS + rows, max_issues=5)
    assert plan.issues.errors == 30
    stored = plan.issues.as_dicts()
    assert len(stored) == 6 and stored[-1]["code"] == "issues_truncated"
    assert "30 errors" in plan.summary()


def test_empty_table_is_an_error():
    assert "no_mappings" in codes(plan_for(HEADER + COLUMNS), "error")

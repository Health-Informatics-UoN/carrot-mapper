"""
Parsing and full validation of SSSOM files for the registry (libs/registry_import).
Pure functions: no database or storage.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from libs.registry_import.full_validate_and_load_checks import (
    CARROT_MAPPING_SET_NAMESPACE,
    DRAFT,
    PUBLISHED,
    STAGING_COLUMNS,
    LicenseRow,
    SetOwner,
    Vocabulary,
    build_import,
    carrot_term_parts,
    check_set_owner,
    check_set_uri_not_reserved,
    check_set_version_is_newer,
    match_license,
    series_id_for,
    set_owner_error,
    set_uri_uuid,
)
from libs.registry_import.full_validate_and_load_parse import decode, parse_sssom
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
HEADER = """\
#curie_map:
#  HP: http://purl.obolibrary.org/obo/HP_
#  MP: http://purl.obolibrary.org/obo/MP_
#mapping_set_id: https://example.org/sets/hp-mp
#mapping_set_version: "1.0.0"
#mapping_set_title: HP to MP
#license: https://creativecommons.org/licenses/by/4.0/
"""
COLUMNS = "subject_id\tsubject_label\tpredicate_id\tobject_id\tobject_label\tmapping_justification\tconfidence\n"
ROW = "HP:0000175\tCleft palate\tskos:exactMatch\tMP:0000111\tcleft palate\tsemapv:LexicalMatching\t0.9\n"


def plan_for(
    text: str,
    overrides=None,
    max_issues=1000,
    license_id="CC-BY-4.0",
    series_set_uri=None,
    file_license_id="CC-BY-4.0",
):
    """
    build_import, with the License id the request names (checked earlier) and
    the License the file's license IRI stands for (looked up earlier).
    """
    return build_import(
        parse_sssom(text),
        VOCAB,
        overrides,
        license_id=license_id,
        max_issues=max_issues,
        series_set_uri=series_set_uri,
        file_license_id=file_license_id,
    )


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
    assert parsed.metadata["mapping_set_version"] == "1.0.0"
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
    assert record.set_version == "1.0.0"
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
    plan = plan_for(path.read_text(encoding="utf-8"), {"set_version": "1.0.0"})
    assert plan.ok, plan.issues.as_dicts()
    assert plan.rows


def test_extension_slots_and_unknown_columns_go_to_extra_metadata():
    path = SPEC_DIR / "examples" / "schema" / "extension-slots.sssom.tsv"
    plan = plan_for(path.read_text(encoding="utf-8"), {"set_version": "1.0.0"})
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
    text = HEADER.replace('#mapping_set_version: "1.0.0"\n', "") + COLUMNS + ROW
    plan = plan_for(text)
    assert "missing_metadata_slot" in codes(plan, "error")

    plan = plan_for(
        text, {"set_version": "2.0.0", "title": "New title", "status": DRAFT}
    )
    assert plan.ok
    assert plan.mapping_set.set_version == "2.0.0"
    assert plan.mapping_set.title == "New title"
    assert plan.status == DRAFT
    assert codes(plan) == ["metadata_overridden"]  # the title differed


FILE_ID = "https://example.org/sets/hp-mp"
NO_ID = HEADER.replace(f"#mapping_set_id: {FILE_ID}\n", "") + COLUMNS + ROW


@pytest.mark.parametrize(
    "text, request_id, series_set_uri, set_uri, code",
    [
        # file id, no request: the file's
        (HEADER + COLUMNS + ROW, None, None, FILE_ID, None),
        # the request agrees with the file
        (HEADER + COLUMNS + ROW, FILE_ID, None, FILE_ID, None),
        (HEADER + COLUMNS + ROW, None, FILE_ID, FILE_ID, None),
        # the request disagrees with the file
        (
            HEADER + COLUMNS + ROW,
            "https://x/other",
            None,
            FILE_ID,
            "mapping_set_id_mismatch",
        ),
        (
            HEADER + COLUMNS + ROW,
            None,
            "https://x/other",
            FILE_ID,
            "mapping_set_id_mismatch",
        ),
        # no file id: the request's, with a warning
        (
            NO_ID,
            None,
            "https://x/series",
            "https://x/series",
            "mapping_set_id_not_in_file",
        ),
        (NO_ID, "https://x/req", None, "https://x/req", "mapping_set_id_not_in_file"),
        # the set_uri override and the series disagree
        (
            NO_ID,
            "https://x/req",
            "https://x/series",
            "https://x/series",
            "mapping_set_id_mismatch",
        ),
    ],
)
def test_mapping_set_id_resolution(text, request_id, series_set_uri, set_uri, code):
    overrides = {"set_uri": request_id} if request_id else None
    plan = plan_for(text, overrides, series_set_uri=series_set_uri)
    assert plan.mapping_set.set_uri == set_uri
    assert "metadata_overridden" not in codes(plan)
    if code is None:
        assert plan.ok and codes(plan) == []
    else:
        assert code in codes(plan)
        assert plan.ok == (code == "mapping_set_id_not_in_file")


def test_file_without_mapping_set_id_gets_a_new_carrot_id():
    plan = plan_for(NO_ID)
    assert plan.ok
    assert codes(plan) == ["mapping_set_id_not_in_file"]
    set_uri = plan.mapping_set.set_uri
    assert set_uri.startswith(CARROT_MAPPING_SET_NAMESPACE)
    # so its series id is the uuid in it, and the set_uri opens the set page
    assert series_id_for(set_uri) == set_uri_uuid(set_uri)
    assert plan_for(NO_ID).mapping_set.set_uri != set_uri


def test_series_id_for():
    sr = "0b7b3c1e-7a39-4a0a-9f3c-5a3e0c2f6a11"
    assert series_id_for(f"{CARROT_MAPPING_SET_NAMESPACE}{sr}") == sr
    # anything else gets a new random id
    for set_uri in (
        "http://pretendurl.com",
        f"{CARROT_MAPPING_SET_NAMESPACE}not-a-uuid",
        f"https://example.org/{sr}",
    ):
        assert series_id_for(set_uri) != series_id_for(set_uri)


def test_unknown_override_and_bad_status():
    plan = plan_for(HEADER + COLUMNS + ROW, {"colour": "red", "status": "LIVE"})
    assert "unknown_override" in codes(plan, "warning")
    assert "invalid_override" in codes(plan, "error")


def test_yaml_float_version_is_read_as_text_with_warning():
    plan = plan_for(HEADER.replace('"1.0.0"', "1.0") + COLUMNS + ROW)
    assert plan.mapping_set.set_version == "1.0"
    assert "coerced_value" in codes(plan, "warning")
    # ...and then isn't a valid version
    assert codes(plan, "error") == ["invalid_set_version"]


def test_yaml_date_version_is_an_iso_date_version():
    plan = plan_for(HEADER.replace('"1.0.0"', "2026-11-04") + COLUMNS + ROW)
    assert plan.ok, plan.issues.as_dicts()
    assert plan.mapping_set.set_version == "2026-11-04"


@pytest.mark.parametrize(
    "version",
    [
        "1.0",
        "1",
        "v1.0.0",
        "01.0.0",
        "1.0.0-rc.1",
        "2026-13-01",
        "2026-1-4",
        # a trailing newline would slip past a "$"-anchored match
        "1.0.0\n",
        "2026-11-04\n",
        # parts over 9 digits don't fit the API's version ordering
        "1000000000.0.0",
        "99999999999.0.0",
    ],
)
def test_set_version_must_be_semver_or_iso_date(version):
    plan = plan_for(HEADER + COLUMNS + ROW, {"set_version": version})
    assert codes(plan, "error") == ["invalid_set_version"]


CC_BY_IRI = "https://creativecommons.org/licenses/by/4.0/"
CC0_IRI = "https://spdx.org/licenses/CC0-1.0.html"
NO_LICENSE = HEADER.replace(f"#license: {CC_BY_IRI}\n", "") + COLUMNS + ROW


@pytest.mark.parametrize(
    "text, file_license_id, license_id, linked, error, warning",
    [
        # the file's IRI is the request's License (here via a see_also alias)
        (HEADER + COLUMNS + ROW, "CC-BY-4.0", "CC-BY-4.0", "CC-BY-4.0", None, None),
        # the file's IRI is another License
        (
            HEADER + COLUMNS + ROW,
            "CC-BY-4.0",
            "CC0-1.0",
            None,
            "license_mismatch",
            None,
        ),
        # the file's IRI is no License, but the request names one
        (HEADER + COLUMNS + ROW, None, "CC0-1.0", None, "license_mismatch", None),
        # no request License: the file's is linked
        (HEADER + COLUMNS + ROW, "CC-BY-4.0", None, "CC-BY-4.0", None, None),
        # no request License and an unknown IRI: kept unlinked
        (HEADER + COLUMNS + ROW, None, None, None, None, "unknown_license"),
        # no license in the file: the request's, with a warning
        (NO_LICENSE, None, "CC0-1.0", "CC0-1.0", None, "license_not_in_file"),
        # no license anywhere
        (NO_LICENSE, None, None, None, "missing_metadata_slot", None),
    ],
)
def test_license_resolution(text, file_license_id, license_id, linked, error, warning):
    overrides = {"license": CC0_IRI} if license_id == "CC0-1.0" else None
    plan = plan_for(
        text, overrides, license_id=license_id, file_license_id=file_license_id
    )
    # (the SSSOM schema also requires a license: schema_violation)
    errors = [c for c in codes(plan, "error") if c != "schema_violation"]
    assert errors == ([error] if error else [])
    assert codes(plan, "warning") == ([warning] if warning else [])
    assert "metadata_overridden" not in codes(plan)
    assert plan.mapping_set.license_id == linked


def test_unknown_license_iri_is_kept_in_extra_metadata():
    plan = plan_for(HEADER + COLUMNS + ROW, license_id=None, file_license_id=None)
    assert plan.ok
    assert plan.mapping_set.license_id is None
    assert plan.mapping_set.extra_metadata["license"] == CC_BY_IRI


def test_linked_license_is_not_in_extra_metadata():
    for text, file_license_id in (
        (HEADER + COLUMNS + ROW, "CC-BY-4.0"),
        (NO_LICENSE, None),
    ):
        plan = plan_for(
            text,
            {"license": "https://spdx.org/licenses/CC-BY-4.0.html"},
            file_license_id=file_license_id,
        )
        assert plan.ok and plan.mapping_set.license_id == "CC-BY-4.0"
        assert "license" not in plan.mapping_set.extra_metadata


SPDX_ROWS = [
    LicenseRow(
        "CC-BY-4.0",
        "https://spdx.org/licenses/CC-BY-4.0.html",
        ("https://creativecommons.org/licenses/by/4.0/legalcode",),
    ),
    LicenseRow(
        "CC0-1.0",
        "https://spdx.org/licenses/CC0-1.0.html",
        ("https://creativecommons.org/publicdomain/zero/1.0/legalcode",),
    ),
    LicenseRow("GPL-2.0", "https://spdx.org/licenses/GPL-2.0.html", (), True),
    LicenseRow("GPL-2.0-only", "https://spdx.org/licenses/GPL-2.0-only.html"),
]


@pytest.mark.parametrize(
    "iri, license_id",
    [
        ("https://spdx.org/licenses/CC-BY-4.0.html", "CC-BY-4.0"),
        ("https://spdx.org/licenses/CC-BY-4.0", "CC-BY-4.0"),
        ("https://creativecommons.org/licenses/by/4.0/legalcode", "CC-BY-4.0"),
        # what SSSOM files usually cite: the deed, not the legal code
        ("https://creativecommons.org/licenses/by/4.0/", "CC-BY-4.0"),
        ("http://creativecommons.org/licenses/by/4.0", "CC-BY-4.0"),
        ("https://www.creativecommons.org/licenses/by/4.0/legalcode.en", "CC-BY-4.0"),
        ("https://creativecommons.org/publicdomain/zero/1.0/", "CC0-1.0"),
        # an exact license_iri wins over a deprecated one
        ("https://spdx.org/licenses/GPL-2.0.html", "GPL-2.0"),
        ("https://creativecommons.org/licenses/by-sa/4.0/", None),
        ("https://example.org/my-licence", None),
        ("", None),
    ],
)
def test_match_license(iri, license_id):
    assert match_license(iri, SPDX_ROWS) == license_id


def test_match_license_prefers_exact_then_not_deprecated():
    rows = [
        LicenseRow("OLD", "https://example.org/l/", (), True),
        LicenseRow("NEW", "https://example.org/l.html"),
        LicenseRow("EXACT", "https://example.org/l"),
    ]
    assert match_license("https://example.org/l", rows) == "EXACT"
    # no exact match: the one SPDX hasn't deprecated
    assert match_license("http://example.org/l/legalcode", rows[:2]) == "NEW"


def test_include_author_orcid_ids_is_a_known_override():
    plan = plan_for(HEADER + COLUMNS + ROW, {"include_author_orcid_ids": True})
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


def test_too_long_namespace_is_an_error():
    namespace = "http://example.org/" + "x" * 1000
    text = HEADER.replace("#curie_map:\n", f"#curie_map:\n#  long: {namespace}\n")
    plan = plan_for(text + COLUMNS + ROW)
    assert not plan.ok
    assert "value_too_long" in codes(plan, "error")


def test_registry_namespace_under_another_name_is_canonicalised():
    text = HEADER.replace(
        "#curie_map:\n",
        "#curie_map:\n#  athena: https://athena.ohdsi.org/search-terms/terms/\n",
    )
    plan = plan_for(text + COLUMNS + ROW.replace("MP:0000111", "athena:8507"))
    assert plan.ok, plan.issues.as_dicts()
    assert row(plan)["object_iri"] == "OMOP:8507"
    assert row(plan)["object_prefix"] == "OMOP"


def plan_with_prefixes(text: str, prefixes: dict[str, str]):
    """build_import against a registry that already has ``prefixes``."""
    return build_import(
        parse_sssom(text),
        replace(VOCAB, prefixes=prefixes),
        license_id="CC-BY-4.0",
        file_license_id="CC-BY-4.0",
    )


def test_terms_prefixes_are_listed_for_registration():
    plan = plan_for(HEADER + COLUMNS + ROW)
    assert plan.prefixes == {
        "HP": "http://purl.obolibrary.org/obo/HP_",
        "MP": "http://purl.obolibrary.org/obo/MP_",
    }


def test_registered_namespace_under_another_name_is_canonicalised():
    plan = plan_with_prefixes(
        HEADER + COLUMNS + ROW, {"mp": "http://purl.obolibrary.org/obo/MP_"}
    )
    assert plan.ok, plan.issues.as_dicts()
    assert row(plan)["object_iri"] == "mp:0000111"
    assert plan.prefixes["mp"] == "http://purl.obolibrary.org/obo/MP_"
    # The stored curie_map can expand the stored CURIE, and keeps the file's name
    assert plan.mapping_set.curie_map["mp"] == "http://purl.obolibrary.org/obo/MP_"
    assert plan.mapping_set.curie_map["MP"] == "http://purl.obolibrary.org/obo/MP_"


def test_registry_binding_wins_over_an_unused_file_prefix_of_the_same_name():
    # The file's "mp" is never used; its MP_ terms are stored as mp: (the
    # registry's name), so the stored curie_map must bind mp as the registry does.
    text = HEADER.replace(
        "#curie_map:\n", "#curie_map:\n#  mp: http://example.org/other/\n"
    )
    plan = plan_with_prefixes(
        text + COLUMNS + ROW, {"mp": "http://purl.obolibrary.org/obo/MP_"}
    )
    assert plan.ok, plan.issues.as_dicts()
    assert row(plan)["object_iri"] == "mp:0000111"
    assert plan.mapping_set.curie_map["mp"] == "http://purl.obolibrary.org/obo/MP_"


@pytest.mark.parametrize(
    "namespace",
    [
        "banana",
        "urn:example:",
        "ftp://example.org/x/",
        "http:///no-host/",
        "http://example.org/with space/",
    ],
)
def test_namespace_must_be_an_absolute_http_iri(namespace):
    text = HEADER.replace("#curie_map:\n", f"#curie_map:\n#  X: '{namespace}'\n")
    plan = plan_for(text + COLUMNS + ROW)
    assert not plan.ok
    assert "invalid_namespace" in codes(plan, "error")


def test_registered_name_for_another_namespace_is_an_error_where_used():
    registry = {"MP": "http://example.org/another-tre/"}
    plan = plan_with_prefixes(HEADER + COLUMNS + ROW, registry)
    assert codes(plan, "error") == ["prefix_conflict"]
    assert "give that namespace another prefix name" in plan.issues.items[0].message

    # Declared but unused: nothing is stored under it, so no error
    unused = HEADER.replace(
        "#mapping_set_id", "#  extra: http://example.org/x/\n#mapping_set_id"
    )
    plan = plan_with_prefixes(
        unused + COLUMNS + ROW, {"extra": "http://example.org/another-tre/"}
    )
    assert plan.ok, plan.issues.as_dicts()


def test_two_names_for_a_new_namespace_become_one():
    text = HEADER.replace(
        "#  MP: http://purl.obolibrary.org/obo/MP_\n",
        "#  MP: http://purl.obolibrary.org/obo/MP_\n#  MPalias: http://purl.obolibrary.org/obo/MP_\n",
    )
    plan = plan_for(
        text
        + COLUMNS
        + ROW
        + ROW.replace("MP:0000111", "MPalias:0000111").replace("0.9", "0.8")
    )
    assert "duplicate_mapping" in codes(plan, "error")


@pytest.mark.parametrize(
    "owner, origin, scan_report_id, user_id, allowed",
    [
        (None, "SSSOM_UPLOAD", None, 1, True),
        (SetOwner(None, 1), "SSSOM_UPLOAD", None, 1, True),
        (SetOwner(None, 1), "SSSOM_UPLOAD", None, 2, False),
        (SetOwner(None, None), "SSSOM_UPLOAD", None, None, False),
        (SetOwner(7, 1), "CARROT_DIRECT_PUBLISH", 7, 2, True),
        (SetOwner(7, 1), "CARROT_DIRECT_PUBLISH", 8, 1, False),
        (SetOwner(None, 1), "CARROT_DIRECT_PUBLISH", 7, 1, False),
    ],
)
def test_set_owner_error(owner, origin, scan_report_id, user_id, allowed):
    error = set_owner_error(
        owner, origin=origin, scan_report_id=scan_report_id, user_id=user_id
    )
    assert (error is None) == allowed


def test_set_owner_check_adds_an_error():
    plan = plan_for(HEADER + COLUMNS + ROW)
    check_set_owner(plan, None)
    assert plan.ok
    check_set_owner(plan, "it was published by another user")
    assert codes(plan, "error") == ["set_uri_not_owned"]


SR_UUID = "0b9f6c1e-3a4d-4c55-9a51-2f6d8e7b1c20"


@pytest.mark.parametrize(
    "set_uri, expected",
    [
        (f"https://carrot.ac.uk/registry/mapping-sets/{SR_UUID}", SR_UUID),
        (f"https://carrot.ac.uk/registry/mapping-sets/{SR_UUID.upper()}/", SR_UUID),
        ("https://carrot.ac.uk/registry/mapping-sets/7", None),
        ("https://example.org/sets/hp-mp", None),
        ("", None),
    ],
)
def test_set_uri_uuid(set_uri, expected):
    assert set_uri_uuid(set_uri) == expected


@pytest.mark.parametrize(
    "origin, local_scan_report_id, allowed",
    [
        # a scan report on this instance: direct publish only
        ("SSSOM_UPLOAD", 7, False),
        ("CARROT_DIRECT_PUBLISH", 7, True),
        # another instance's scan report (a TRE's export), or not Carrot's
        ("SSSOM_UPLOAD", None, True),
    ],
)
def test_local_scan_report_sets_are_reserved_for_direct_publish(
    origin, local_scan_report_id, allowed
):
    plan = plan_for(HEADER + COLUMNS + ROW)
    check_set_uri_not_reserved(plan, origin, local_scan_report_id)
    assert plan.ok == allowed
    if not allowed:
        assert codes(plan, "error") == ["set_uri_reserved"]


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
    plan = plan_for(path.read_text(encoding="utf-8"), {"set_version": "1.0.0"})
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


@pytest.mark.parametrize(
    "version, existing",
    [
        ("1.0.0", []),
        ("1.0.1", ["1.0.0"]),
        ("1.10.0", ["1.9.3", "1.2.0"]),
        ("2.0.0", ["1.9.9"]),
        ("2026-11-04", ["2026-11-03", "2025-12-31"]),
    ],
)
def test_set_version_higher_than_existing_is_accepted(version, existing):
    plan = plan_for(HEADER + COLUMNS + ROW, {"set_version": version})
    check_set_version_is_newer(plan, existing)
    assert plan.ok, plan.issues.as_dicts()


@pytest.mark.parametrize(
    "version, existing, code",
    [
        ("1.0.0", ["1.0.0"], "set_version_exists"),
        ("1.9.0", ["1.10.0"], "set_version_not_newer"),
        ("1.0.1", ["2.0.0", "1.0.0"], "set_version_not_newer"),
        ("2026-11-03", ["2026-11-04"], "set_version_not_newer"),
        ("2026-11-04", ["1.0.0"], "set_version_scheme_mismatch"),
        ("2.0.0", ["2026-11-04"], "set_version_scheme_mismatch"),
    ],
)
def test_set_version_not_higher_than_existing_is_an_error(version, existing, code):
    plan = plan_for(HEADER + COLUMNS + ROW, {"set_version": version})
    check_set_version_is_newer(plan, existing)
    assert codes(plan, "error") == [code]
    assert plan.issues.items[-1].message.startswith(
        "Mapping set https://example.org/sets/hp-mp: "
    )


def test_malformed_set_version_is_only_reported_once():
    plan = plan_for(HEADER + COLUMNS + ROW, {"set_version": "1.0"})
    check_set_version_is_newer(plan, ["1.0"])
    assert codes(plan, "error") == ["invalid_set_version"]

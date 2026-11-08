"""
Check the SSSOM rules export against the SSSOM 1.0.0 specification.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import jsonschema
import pytest
import yaml
from libs.rules_export.sssom import write_sssom_tsv

SPEC_DIR = Path(__file__).parent / "sssom_spec"
JSON_SCHEMA = json.loads((SPEC_DIR / "sssom_schema.schema.json").read_text())
LINKML = yaml.safe_load((SPEC_DIR / "sssom_schema.yaml").read_text())

MAPPING_SET_SLOTS = set(JSON_SCHEMA["$defs"]["MappingSet"]["properties"])
MAPPING_SLOTS = set(JSON_SCHEMA["$defs"]["Mapping"]["properties"])
# Slots whose values are identifiers, which must be written as CURIEs in TSV.
ENTITY_REFERENCE_SLOTS = {
    name
    for name, slot in LINKML["slots"].items()
    if (slot or {}).get("range") == "EntityReference"
}

# spec-intro.md, "IRI prefixes": built-in prefixes, which MUST NOT be redefined.
BUILTIN_PREFIXES = {
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "semapv": "https://w3id.org/semapv/vocab/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "sssom": "https://w3id.org/sssom/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "linkml": "https://w3id.org/linkml/",
}

NCNAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]*$")
CURIE = re.compile(r"^(?P<prefix>[A-Za-z_][A-Za-z0-9_.\-]*):(?P<local>.*)$")


def _schema_type(defn: dict) -> set[str]:
    if "type" in defn:
        t = defn["type"]
        return {t} if isinstance(t, str) else set(t)
    types: set[str] = set()
    for option in defn.get("anyOf", []):
        types |= _schema_type(option)
    return types


def split_tsv_fields(block: str) -> tuple[list[list[str]], list[str]]:
    """
    Tokenise the mappings block exactly per spec-formats-tsv.md "Quoting"
    (RFC 4180 adapted to tabs), reporting any value that breaks the rules.
    """
    errors: list[str] = []
    rows: list[list[str]] = []
    row: list[str] = []
    i, n = 0, len(block)
    while i < n:
        if block[i] == '"':
            # quoted value: "" is an escaped quote; ends at a lone quote
            i += 1
            value = []
            while True:
                if i >= n:
                    errors.append("unterminated quoted value")
                    break
                if block[i] == '"':
                    if i + 1 < n and block[i + 1] == '"':
                        value.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                value.append(block[i])
                i += 1
            field = "".join(value)
            if i < n and block[i] not in "\t\n":
                errors.append(f"text after closing quote in row {len(rows) + 1}")
        else:
            j = i
            while j < n and block[j] not in "\t\n":
                j += 1
            field = block[i:j]
            i = j
            # Quoting rule 2: values with double quotes (or tabs/line breaks, which
            # can't occur here unquoted) MUST be enclosed in double quotes.
            if '"' in field:
                errors.append(
                    f"row {len(rows) + 1}: value {field!r} contains a double quote "
                    "but is not enclosed in double quotes"
                )
        row.append(field)
        if i < n and block[i] == "\t":
            i += 1
            if i == n:
                row.append("")
        elif i < n and block[i] == "\n":
            rows.append(row)
            row = []
            i += 1
    if row:
        rows.append(row)
    return rows, errors


def check_yaml_features(metadata_yaml: str) -> list[str]:
    """spec-formats-tsv.md "Forbidden YAML features"."""
    errors = []
    for event in yaml.parse(metadata_yaml):
        if isinstance(event, yaml.DocumentStartEvent) and (event.version or event.tags):
            errors.append("metadata uses a YAML/TAG directive")
        if isinstance(event, yaml.AliasEvent):
            errors.append("metadata uses a YAML alias")
        if getattr(event, "anchor", None):
            errors.append("metadata uses a YAML anchor")
        tag = getattr(event, "tag", None)
        implicit = getattr(event, "implicit", True)
        if tag and not (
            implicit is True or (isinstance(implicit, tuple) and any(implicit))
        ):
            errors.append(f"metadata uses an explicit YAML tag {tag}")
    return errors


def check_sssom_tsv(text: str) -> list[str]:
    """Return every way ``text`` violates SSSOM 1.0.0 / SSSOM-TSV (empty if none)."""
    errors: list[str] = []

    # --- Encoding: UTF-8, no byte order mark ---------------------------------
    if text.startswith("\ufeff"):
        errors.append("file starts with a byte order mark")

    # --- Metadata block: leading '#' lines, same number of spaces after '#' --
    lines = text.split("\n")
    meta_lines = []
    for line in lines:
        if not line.startswith("#"):
            break
        meta_lines.append(line[1:])
    if not meta_lines:
        return ["no embedded metadata block"]
    indent = len(meta_lines[0]) - len(meta_lines[0].lstrip(" "))
    for line in meta_lines:
        if line.strip() and len(line) - len(line.lstrip(" ")) < indent:
            errors.append("metadata lines have inconsistent spaces after '#'")
            break
    metadata_yaml = "\n".join(line[indent:] for line in meta_lines)
    errors += check_yaml_features(metadata_yaml)
    try:
        metadata = yaml.safe_load(metadata_yaml) or {}
    except yaml.YAMLError as e:
        return errors + [f"metadata is not valid YAML: {e}"]

    # --- Extension definitions (spec-model.md "Non-standard slots") ----------
    ext_defs = metadata.get("extension_definitions") or []
    ext_names = [d.get("slot_name") for d in ext_defs]
    ext_props = [d.get("property") for d in ext_defs if d.get("property")]
    for d in ext_defs:
        name = d.get("slot_name")
        if not name or not NCNAME.match(name):
            errors.append(f"extension slot name {name!r} is not an NCName")
        elif name in MAPPING_SLOTS | MAPPING_SET_SLOTS:
            errors.append(f"extension slot {name!r} clashes with a standard slot")
        if not d.get("property"):
            errors.append(f"extension slot {name!r} SHOULD have a property")
    if len(set(ext_names)) != len(ext_names) or len(set(ext_props)) != len(ext_props):
        errors.append("extension slot names/properties are not unique")
    extension_slots = {n for n in ext_names if n}

    # --- Writers MUST NOT write unknown metadata keys -------------------------
    for key in metadata:
        if key not in MAPPING_SET_SLOTS and key not in extension_slots:
            errors.append(f"unknown metadata key {key!r}")

    # --- Prefixes ------------------------------------------------------------
    curie_map = metadata.get("curie_map") or {}
    for prefix, iri in curie_map.items():
        if prefix in BUILTIN_PREFIXES and iri != BUILTIN_PREFIXES[prefix]:
            errors.append(f"built-in prefix {prefix!r} is redefined as {iri!r}")
    declared = set(curie_map) | set(BUILTIN_PREFIXES)

    def check_curie(slot: str, value: str, where: str) -> None:
        m = CURIE.match(value)
        if not m or m["local"].startswith("//"):
            errors.append(f"{where}: {slot} value {value!r} is not a CURIE")
        elif m["prefix"] not in declared:
            errors.append(f"{where}: prefix {m['prefix']!r} is not declared")

    for slot in ENTITY_REFERENCE_SLOTS & set(metadata):
        values = metadata[slot]
        for v in values if isinstance(values, list) else [values]:
            check_curie(slot, str(v), "metadata")
    for d in ext_defs:
        for key in ("property", "type_hint"):
            if d.get(key) and CURIE.match(d[key]) and not d[key].startswith("http"):
                check_curie(key, d[key], f"extension {d.get('slot_name')}")

    # --- Mappings block --------------------------------------------------------
    block = "\n".join(lines[len(meta_lines) :])
    rows, quote_errors = split_tsv_fields(block)
    errors += quote_errors
    rows = [r for r in rows if r != [""]]
    if not rows:
        return errors + ["no mappings block header"]
    header, data = rows[0], rows[1:]
    if len(set(header)) != len(header):
        errors.append("duplicate column names")
    for column in header:
        if column not in MAPPING_SLOTS and column not in extension_slots:
            errors.append(f"unknown column {column!r}")

    mappings = []
    for row_no, row in enumerate(data, start=1):
        if len(row) != len(header):
            errors.append(
                f"row {row_no} has {len(row)} values, header has {len(header)}"
            )
            continue
        mapping: dict = {}
        for column, value in zip(header, row):
            if value == "" or column not in MAPPING_SLOTS:
                continue
            types = _schema_type(JSON_SCHEMA["$defs"]["Mapping"]["properties"][column])
            if "array" in types:
                values = value.split("|")  # multivalued slots are '|'-separated
                if column in ENTITY_REFERENCE_SLOTS:
                    for v in values:
                        check_curie(column, v, f"row {row_no}")
                mapping[column] = values
            elif "number" in types:
                try:
                    mapping[column] = float(value)
                except ValueError:
                    errors.append(f"row {row_no}: {column} {value!r} is not a number")
            else:
                if column in ENTITY_REFERENCE_SLOTS:
                    check_curie(column, value, f"row {row_no}")
                mapping[column] = value
        mappings.append(mapping)

        # extension values: scalars, and match their type hint
        for d in ext_defs:
            name = d.get("slot_name")
            if name in header:
                value = row[header.index(name)]
                hint = d.get("type_hint", "xsd:string")
                is_integer = hint in (
                    "xsd:integer",
                    BUILTIN_PREFIXES["xsd"] + "integer",
                )
                if value and is_integer and not re.fullmatch(r"[+-]?\d+", value):
                    errors.append(f"row {row_no}: {name} {value!r} is not an integer")

    # "There SHOULD be no empty columns" - as the producer we hold ourselves to it.
    for index, column in enumerate(header):
        if data and all(len(r) == len(header) and r[index] == "" for r in data):
            errors.append(f"column {column!r} is empty in every row")

    # --- Official JSON schema --------------------------------------------------
    document = {k: v for k, v in metadata.items() if k not in extension_slots}
    document["mappings"] = mappings
    schema = dict(JSON_SCHEMA)
    schema["$ref"] = "#/$defs/MappingSet"
    validator = jsonschema.Draft201909Validator(
        schema, format_checker=jsonschema.Draft201909Validator.FORMAT_CHECKER
    )
    for error in validator.iter_errors(document):
        path = "/".join(str(p) for p in error.absolute_path)
        errors.append(f"schema: {path or '<set>'}: {error.message[:200]}")

    return errors


# ---------------------------------------------------------------------------
# The checker itself: accepts official examples, rejects broken files
# ---------------------------------------------------------------------------

EXAMPLES = sorted((SPEC_DIR / "examples").glob("*.sssom.tsv"))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_checker_accepts_official_examples(path):
    assert len(EXAMPLES) == 2
    assert check_sssom_tsv(path.read_text(encoding="utf-8")) == []


def test_checker_accepts_official_literal_mappings_example():
    """Value mappings are literal mappings (spec-model.md, "Literal mappings")."""
    path = SPEC_DIR / "examples" / "schema" / "literals.sssom.tsv"
    assert check_sssom_tsv(path.read_text(encoding="utf-8")) == []


def test_checker_accepts_official_defined_extensions_example():
    """
    SSSOM's own extension-slots example uses defined extensions the way we do
    (ext_ names, typed definitions, a set-level extension), and also two
    deliberately *undefined* ones. The checker holds files to "defined extensions
    only", so it must flag exactly those two and nothing else.
    """
    path = SPEC_DIR / "examples" / "schema" / "extension-slots.sssom.tsv"
    errors = check_sssom_tsv(path.read_text(encoding="utf-8"))
    assert errors, "the undefined extensions should be flagged"
    assert all("undeclared" in e for e in errors), errors


CREATED = datetime(2026, 11, 3, tzinfo=UTC)


def rule(**overrides):
    """One row of the temp rules table, as Mapper's rules export query returns it."""
    base = {
        "sr_concept_id": 7,
        "source_table": "demographics.csv",
        "source_field": "sex",
        "term_mapping_value": "F",
        "dest_table": "person",
        "dest_field": "gender_concept_id",
        "concept_id": 8532,
        "concept_name": "FEMALE",
        "concept_domain": "Gender",
        "concept_vocabulary": "Gender",
        "vocabulary_version": "v5.0 01-OCT-26",
        "creation_type": "M",
        "confidence": 0.9,
        "mapping_tool": "carrot-mapper",
        "mapping_tool_version": "3.1.0",
        "created_at": datetime(2026, 1, 2, 9, 30),
        "description": "checked by data manager",
    }
    base.update(overrides)
    return base


MALE = {
    "sr_concept_id": 8,
    "created_at": datetime(2026, 2, 3, 10, 0),
    "term_mapping_value": "M",
    "concept_id": 8507,
    "concept_name": "MALE",
}
SMOKING = {
    "sr_concept_id": 9,
    "dest_table": "observation",
    "source_field": "smoking",
    "term_mapping_value": '"never" smoked',
    "concept_id": 4144272,
    "concept_name": 'Never smoked tobacco ("lifelong")',
    "concept_domain": "Observation",
    "concept_vocabulary": "SNOMED",
    "vocabulary_version": "2026-09-01 SNOMEDCT-US",
    "description": "note with\ttab and\nnew line",
    "creation_type": "V",
}
# a field mapping: the whole "weight" column is mapped to one concept
WEIGHT = {
    "sr_concept_id": 10,
    "dest_table": "measurement",
    "source_field": "weight",
    "term_mapping_value": None,
    "concept_id": 3025315,
    "concept_name": "Body weight",
    "concept_domain": "Measurement",
    "concept_vocabulary": "LOINC",
    "vocabulary_version": "LOINC 2.80",
    "description": None,
}
PERSON_ID = {"source_field": "id", "dest_field": "person_id"}

RULES = [
    rule(),
    rule(dest_field="gender_source_concept_id"),
    rule(dest_field="gender_source_value"),
    rule(**PERSON_ID),
    rule(**MALE),
    rule(**MALE, dest_field="gender_source_value"),
    rule(**MALE, **PERSON_ID),
    rule(**SMOKING, dest_field="observation_concept_id"),
    rule(**SMOKING, dest_field="observation_source_value"),
    rule(**{**SMOKING, **PERSON_ID}),
    rule(**WEIGHT, dest_field="measurement_concept_id"),
    rule(**WEIGHT, dest_field="value_as_number"),
    rule(**{**WEIGHT, **PERSON_ID}),
]


def carrot_export(rules=RULES) -> str:
    return write_sssom_tsv(
        rules,
        "Dataset: test",
        42,
        created=CREATED,
        omop_vocabulary_version="v5.0 27-FEB-25",
        mapper_version="4.3.1",
    )


def mutate(text: str, old: str, new: str) -> str:
    assert old in text, old
    return text.replace(old, new, 1)


@pytest.mark.parametrize(
    "old, new, expected",
    [
        ("license:", "lizence:", "unknown metadata key 'lizence'"),
        ("mapping_set_id:", "mapping_set_idx:", "'mapping_set_id' is a required"),
        (
            "semapv:ManualMappingCuration",
            "semapv:Guesswork",
            "schema: mappings/0/mapping_justification",
        ),
        (
            "skos:exactMatch",
            "http://www.w3.org/2004/02/skos/core#exactMatch",
            "is not a CURIE",
        ),
        ("OMOP:8532", "NOTDECLARED:8532", "prefix 'NOTDECLARED' is not declared"),
        (
            "curie_map:\n",
            "curie_map:\n#  skos: http://example.org/skos#\n",
            "built-in prefix 'skos' is redefined",
        ),
        ("\tobject_label\t", "\tmade_up_column\t", "unknown column 'made_up_column'"),
        ("\t0.9\t", "\t1.5\t", "schema: mappings/0/confidence"),
        ("\t2026-01-02\t", "\t02/01/2026\t", "schema: mappings/0/mapping_date"),
        (
            "slot_name: ext_omop_vocabulary_version",
            "slot_name: subject_id",
            "clashes with a standard slot",
        ),
        ("#license", "#&anchor license", "YAML anchor"),
    ],
)
def test_checker_rejects_broken_files(old, new, expected):
    errors = check_sssom_tsv(mutate(carrot_export(), old, new))
    assert any(expected in e for e in errors), errors


def test_checker_rejects_unquoted_double_quote():
    # a value containing a double quote, written without the required quoting
    text = mutate(carrot_export(), '"""never"" smoked"', 'never "smoked"')
    errors = check_sssom_tsv(text)
    assert any("contains a double quote" in e for e in errors), errors


# ---------------------------------------------------------------------------
# The Carrot export
# ---------------------------------------------------------------------------


def test_carrot_export_conforms_to_sssom():
    assert check_sssom_tsv(carrot_export()) == []


def test_carrot_export_conforms_with_minimal_rules():
    """Optional slots absent everywhere -> those columns are left out entirely."""
    minimal = [
        {
            k: v
            for k, v in r.items()
            if k not in ("confidence", "description", "mapping_tool_version")
        }
        for r in RULES[:4]
    ]
    text = carrot_export(minimal)
    assert check_sssom_tsv(text) == []
    header = next(line for line in text.splitlines() if not line.startswith("#"))
    assert "confidence" not in header.split("\t")
    assert "comment" not in header.split("\t")


def test_carrot_export_round_trips_awkward_values():
    rows, errors = split_tsv_fields(
        "\n".join(
            line for line in carrot_export().split("\n") if not line.startswith("#")
        )
    )
    assert errors == []
    header = rows[0]
    smoking = next(
        r
        for r in rows[1:]
        if r[header.index("subject_id")].startswith("carrot:smoking/")
    )
    assert smoking[header.index("subject_label")] == '"never" smoked'
    assert smoking[header.index("comment")] == "note with\ttab and\nnew line"
    assert smoking[header.index("object_label")] == 'Never smoked tobacco ("lifelong")'


def test_checker_rejects_empty_column():
    lines = carrot_export().split("\n")
    header_at = next(i for i, line in enumerate(lines) if not line.startswith("#"))
    lines[header_at] += "\tsee_also"
    for i in range(header_at + 1, len(lines)):
        if lines[i]:
            lines[i] += "\t"
    errors = check_sssom_tsv("\n".join(lines))
    assert "column 'see_also' is empty in every row" in errors, errors


def test_carrot_export_subjects_and_cardinality():
    """Subjects are carrot:<field>[/<value>]; every row has a cardinality."""
    table, errors = split_tsv_fields(
        "\n".join(
            line for line in carrot_export().split("\n") if not line.startswith("#")
        )
    )
    assert errors == []
    header = table[0]
    rows = [dict(zip(header, r)) for r in table[1:] if r != [""]]
    assert [(r["subject_id"], r["subject_label"], r["object_id"]) for r in rows] == [
        ("carrot:sex/F", "F", "OMOP:8532"),
        ("carrot:sex/M", "M", "OMOP:8507"),
        ("carrot:smoking/%22never%22%20smoked", '"never" smoked', "OMOP:4144272"),
        ("carrot:weight", "weight", "OMOP:3025315"),
    ]
    assert {r["mapping_cardinality"] for r in rows} == {"1:1"}
    # person_id / date rules aren't mappings, and there are no extension columns
    assert not [c for c in header if c.startswith("ext_")]

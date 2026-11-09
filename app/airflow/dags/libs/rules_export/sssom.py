"""
Serialise a scan report's concept mappings as an SSSOM (Simple Standard for Sharing
Ontological Mappings) TSV file: https://mapping-commons.github.io/sssom/

One row per mapping, from a source field (``carrot:<field>``) or a value in a field
(``carrot:<field>/<value>``) to an OMOP concept (``OMOP:<concept_id>``). The row's
``other`` column names the concept's vocabulary (``vocab:<vocabulary_id>``) and
``object_source_version`` gives that vocabulary's version.

The metadata block holds the tool, its version and the publication date, plus the
mapping date when every mapping shares one.
"""

from __future__ import annotations

import csv
import io
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import Any
from urllib.parse import quote

import yaml

MAPPING_TOOL = "carrot-mapper"

# carrot:<field>[/<value>] subjects. The same namespace on every Carrot instance, so
# the same term has the same IRI everywhere.
SUBJECT_PREFIX = "carrot"
SUBJECT_IRI = "https://carrot.ac.uk/sssom/terms/"
OMOP_CONCEPT_PREFIX = "OMOP"

CURIE_MAP = {
    SUBJECT_PREFIX: SUBJECT_IRI,
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "semapv": "https://w3id.org/semapv/vocab/",
}

# Carrot doesn't record how close a match is (exact, broader, narrower...), so every
# mapping is asserted as an exact match.
PREDICATE = "skos:exactMatch"

# Carrot ScanReportConcept.creation_type -> SEMAPV mapping justification.
MAPPING_JUSTIFICATIONS = {
    "M": "semapv:ManualMappingCuration",  # chosen by a user
    "V": "semapv:LexicalMatching",  # source code matched to concept_code in a vocabulary
    "R": "semapv:MappingChaining",  # reused from an existing manual mapping
    "X": "semapv:LexicalMatching",  # source term matched to concept_name in a domain
}
DEFAULT_JUSTIFICATION = "semapv:UnspecifiedMatching"

COLUMNS = [
    "subject_id",
    "subject_label",
    "predicate_id",
    "object_id",
    "object_label",
    "object_category",
    "other",
    "object_source_version",
    "mapping_justification",
    "mapping_cardinality",
    "confidence",
    "mapping_date",
    "comment",
]

# Always written as columns: the slots SSSOM requires on every mapping, and the
# vocabulary, its version and the cardinality (people look for them per mapping).
# Other columns are omitted when empty in every row.
ALWAYS_COLUMNS = {
    "subject_id",
    "subject_label",
    "predicate_id",
    "object_id",
    "mapping_justification",
    "other",
    "object_source_version",
    "mapping_cardinality",
}


def _clean(value: Any) -> str:
    """Normalise a DB/pandas value to a string; None/NaN/NaT become ''."""
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    # pandas NaT / NA compare unequal to themselves
    try:
        if value != value:  # noqa: PLR0124 - deliberate NaN/NaT/NA check
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).replace("\ufeff", "")


def _clean_int(value: Any) -> str:
    """IDs may come back from pandas as floats (e.g. 8507.0)."""
    value = _clean(value)
    return str(int(float(value))) if value else ""


def _encode(name: str) -> str:
    """Percent-encode a field name, value or vocabulary for use in a CURIE."""
    return quote(name, safe="-._~")


def subject_id(field: str, value: str = "") -> str:
    """carrot:<field>, or carrot:<field>/<value> for a value mapping."""
    local = _encode(field) + (f"/{_encode(value)}" if value else "")
    return f"{SUBJECT_PREFIX}:{local}"


def is_concept_field(omop_field: str) -> bool:
    return omop_field.endswith("_concept_id")


def _mapping_row(rule: Mapping[str, Any]) -> dict[str, str]:
    """One row for one ScanReportConcept, from one of its *_concept_id rules."""
    sr_concept_id = rule.get("sr_concept_id")
    source_field = _clean(rule.get("source_field"))
    source_value = _clean(rule.get("term_mapping_value"))
    concept_id = _clean_int(rule.get("concept_id"))
    if not concept_id:
        raise ValueError(f"Rule {sr_concept_id} has no concept_id")
    if not source_field:
        raise ValueError(f"Rule {sr_concept_id} has no source_field")

    vocabulary = _clean(rule.get("concept_vocabulary"))
    creation_type = _clean(rule.get("creation_type"))
    return {
        "subject_id": subject_id(source_field, source_value),
        # the value for a value mapping, the field name for a field mapping
        "subject_label": source_value or source_field,
        "predicate_id": PREDICATE,
        "object_id": f"{OMOP_CONCEPT_PREFIX}:{concept_id}",
        "object_label": _clean(rule.get("concept_name")),
        "object_category": _clean(rule.get("concept_domain")),
        "other": f"vocab:{_encode(vocabulary)}" if vocabulary else "",
        "object_source_version": _clean(rule.get("vocabulary_version")),
        "mapping_justification": MAPPING_JUSTIFICATIONS.get(
            creation_type, DEFAULT_JUSTIFICATION
        ),
        "mapping_cardinality": "",  # filled in once all rows are known
        "confidence": _clean(rule.get("confidence")),
        "mapping_date": _clean(rule.get("created_at")),
        "comment": _clean(rule.get("description")),
    }


def set_cardinality(rows: list[dict[str, str]]) -> None:
    """
    Fill mapping_cardinality, counting over the whole file the distinct objects of
    each subject and the distinct subjects of each object (SSSOM spec-model,
    "mapping cardinality"; the same computation as sssom-py's infer_cardinality).
    """
    objects_by_subject: defaultdict[str, set[str]] = defaultdict(set)
    subjects_by_object: defaultdict[str, set[str]] = defaultdict(set)
    for row in rows:
        objects_by_subject[row["subject_id"]].add(row["object_id"])
        subjects_by_object[row["object_id"]].add(row["subject_id"])
    for row in rows:
        many_objects = len(objects_by_subject[row["subject_id"]]) > 1
        many_subjects = len(subjects_by_object[row["object_id"]]) > 1
        row["mapping_cardinality"] = (
            f"{'n' if many_subjects else '1'}:{'n' if many_objects else '1'}"
        )


def build_mapping_rows(rules: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    """
    One SSSOM row per distinct mapping (subject, concept) in the temp-table rules.

    Each ScanReportConcept's row comes from its first ``*_concept_id`` rule; its
    other rules (source value, person_id, dates...) only say how Transform applies
    the mapping. The table isn't part of the subject, so the same field/value mapped
    to the same concept in several tables gives one row.
    """
    seen_concepts: set[str] = set()
    rows: dict[tuple[str, str], dict[str, str]] = {}
    for rule in rules:
        key = _clean_int(rule.get("sr_concept_id"))
        if key in seen_concepts or not is_concept_field(_clean(rule.get("dest_field"))):
            continue
        seen_concepts.add(key)
        row = _mapping_row(rule)
        rows.setdefault((row["subject_id"], row["object_id"]), row)
    result = list(rows.values())
    set_cardinality(result)
    return result


def build_metadata(
    rows: list[dict[str, str]], created: datetime, mapper_version: str | None = None
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "curie_map": dict(CURIE_MAP),
        "mapping_tool": MAPPING_TOOL,
    }
    if mapper_version:
        metadata["mapping_tool_version"] = mapper_version
    # A mapping date shared by every mapping is written once here instead of per row
    # (SSSOM "condensation").
    dates = {r["mapping_date"] for r in rows}
    if len(dates) == 1 and "" not in dates:
        metadata["mapping_date"] = dates.pop()
    metadata["publication_date"] = created.date().isoformat()
    return metadata


def write_sssom_tsv(
    rules: Iterable[Mapping[str, Any]],
    created: datetime | None = None,
    mapper_version: str | None = None,
) -> str:
    """
    Render rules (dict-like rows from the temp rules table) as an SSSOM TSV string.

    Expected keys per rule: sr_concept_id, source_field, term_mapping_value,
    dest_field, concept_id, concept_name, creation_type; and optionally
    concept_domain, concept_vocabulary, vocabulary_version, confidence, created_at,
    description.
    """
    created = created or datetime.now()
    rows = build_mapping_rows(rules)
    metadata = build_metadata(rows, created, mapper_version)

    out = io.StringIO()
    header = yaml.safe_dump(
        metadata, sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    for line in header.splitlines():
        out.write(f"#{line}\n")

    # "There SHOULD be no empty columns": skip optional slots nobody has a value for.
    columns = [
        c
        for c in COLUMNS
        if c not in metadata and (c in ALWAYS_COLUMNS or any(r[c] for r in rows))
    ]

    # csv's QUOTE_MINIMAL with a tab delimiter is exactly the SSSOM/TSV quoting rule:
    # values containing tabs, line breaks or double quotes are enclosed in double
    # quotes, with embedded double quotes doubled.
    writer = csv.writer(
        out, delimiter="\t", quoting=csv.QUOTE_MINIMAL, lineterminator="\n"
    )
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row[c] for c in columns])
    return out.getvalue()

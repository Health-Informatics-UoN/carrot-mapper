"""
Serialise a scan report's concept mappings as an SSSOM (Simple Standard for Sharing
Ontological Mappings) TSV file: https://mapping-commons.github.io/sssom/
"""

from __future__ import annotations

import csv
import io
import math
import os
from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import Any
from urllib.parse import quote

import yaml

# Namespace for identifiers and extension properties minted by Carrot.
CARROT_SSSOM_NAMESPACE = "https://carrot.ac.uk/sssom/"

# Base IRI for this Carrot instance's mapping set IDs. Set it per deployment so
# mapping_set_id is unique across Carrot instances.
SSSOM_BASE_IRI = os.getenv("SSSOM_BASE_IRI", CARROT_SSSOM_NAMESPACE)
# `license` is mandatory in SSSOM (a URI). The default is the "unspecified licence"
# URI that sssom-py uses as its default; the specification itself defines none. Set
# SSSOM_LICENSE if your organisation uses a licence.
SSSOM_LICENSE = os.getenv("SSSOM_LICENSE", "https://w3id.org/sssom/license/unspecified")

MAPPING_TOOL = "carrot-mapper"

# carrot:<field>[/<value>] subjects. The same namespace on every Carrot instance, so
# the same term has the same IRI everywhere.
SUBJECT_PREFIX = "carrot"
SUBJECT_IRI = CARROT_SSSOM_NAMESPACE + "terms/"
# Kept apart from the subject namespace, so a field can't share its IRI with one of
# our extension properties.
EXTENSION_PREFIX = "carrotsssom"
OMOP_CONCEPT_PREFIX = "OMOP"
# Expansion of OMOP: as registered in the Bioregistry (https://bioregistry.io/omop)
OMOP_CONCEPT_IRI = "https://athena.ohdsi.org/search-terms/terms/"
OMOP_VOCABULARY_PREFIX = "omopvocab"

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

# Extension slots written once in the metadata block, describing the whole set.
MAPPING_SET_EXTENSION_SLOTS: list[tuple[str, str]] = [
    ("ext_omop_vocabulary_version", "xsd:string"),
]

COLUMNS = [
    "subject_id",
    "subject_label",
    "predicate_id",
    "object_id",
    "object_label",
    "object_category",
    "object_type",
    "object_source",
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
    "object_source",
    "object_source_version",
    "mapping_cardinality",
}

# Propagatable slots (see the spec's "Condensation") moved to the metadata block
# when every row has the same value.
CONDENSABLE_COLUMNS = ["object_type", "mapping_date"]


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
    return str(value).replace("﻿", "")


def _clean_int(value: Any) -> str:
    """IDs may come back from pandas as floats (e.g. 8507.0)."""
    value = _clean(value)
    return str(int(float(value))) if value else ""


def _encode(name: str) -> str:
    """Percent-encode a field name or value for use in a CURIE's local part."""
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
        "object_type": "skos concept",
        "object_source": (
            f"{OMOP_VOCABULARY_PREFIX}:{_encode(vocabulary)}" if vocabulary else ""
        ),
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


def condense(rows: list[dict[str, str]]) -> dict[str, str]:
    """
    Values to move to the mapping set: propagatable slots that every row shares.
    (SSSOM "condensation": only when *all* mappings have the same, non-empty value.)
    """
    condensed = {}
    for column in CONDENSABLE_COLUMNS:
        values = {r[column] for r in rows}
        if len(values) == 1 and "" not in values:
            condensed[column] = values.pop()
    return condensed


def build_metadata(
    scan_report_name: str,
    scan_report_id: int,
    created: datetime,
    rows: list[dict[str, str]],
    condensed: Mapping[str, str],
    omop_vocabulary_version: str | None = None,
    mapper_version: str | None = None,
) -> dict[str, Any]:
    base = SSSOM_BASE_IRI.rstrip("/") + "/"
    curie_map = {
        SUBJECT_PREFIX: SUBJECT_IRI,
        OMOP_CONCEPT_PREFIX: OMOP_CONCEPT_IRI,
    }
    if any(r["object_source"] for r in rows):
        curie_map[OMOP_VOCABULARY_PREFIX] = CARROT_SSSOM_NAMESPACE + "omop-vocabulary/"
    if omop_vocabulary_version:
        curie_map[EXTENSION_PREFIX] = CARROT_SSSOM_NAMESPACE

    metadata: dict[str, Any] = {
        "curie_map": curie_map,
        "mapping_set_id": f"{base}mapping-sets/scanreport/{scan_report_id}",
        "mapping_set_title": scan_report_name,
        "mapping_set_description": (
            f"Carrot-Mapper mappings from scan report {scan_report_id} "
            f"({scan_report_name}) to OMOP standardised vocabulary concepts."
        ),
        "license": SSSOM_LICENSE,
    }
    if "object_type" in condensed:
        metadata["object_type"] = condensed["object_type"]
    metadata["mapping_tool"] = MAPPING_TOOL
    if mapper_version:
        metadata["mapping_tool_version"] = mapper_version
    if "mapping_date" in condensed:
        metadata["mapping_date"] = condensed["mapping_date"]
    metadata["publication_date"] = created.date().isoformat()

    if omop_vocabulary_version:
        metadata["ext_omop_vocabulary_version"] = omop_vocabulary_version
        metadata["extension_definitions"] = [
            {
                "slot_name": name,
                "property": f"{EXTENSION_PREFIX}:{name}",
                "type_hint": hint,
            }
            for name, hint in MAPPING_SET_EXTENSION_SLOTS
        ]
    return metadata


def write_sssom_tsv(
    rules: Iterable[Mapping[str, Any]],
    scan_report_name: str,
    scan_report_id: int,
    created: datetime | None = None,
    omop_vocabulary_version: str | None = None,
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
    condensed = condense(rows)
    metadata = build_metadata(
        scan_report_name,
        scan_report_id,
        created,
        rows,
        condensed,
        omop_vocabulary_version,
        mapper_version,
    )

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
        if c not in condensed and (c in ALWAYS_COLUMNS or any(r[c] for r in rows))
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

"""
Full validation of an SSSOM file for the registry, and its normalisation into
an ImportPlan: the mapping set's columns plus one staging row per mapping, in
exactly the shape load.py writes. Validation and normalisation are one pass, so
what full_validate accepts is precisely what load inserts.

Checks, each reported as an Issue (see parse.Issue):

- metadata: the official SSSOM 1.0 JSON schema (vendored in libs/sssom_spec),
  plus what the registry needs: mapping_set_id, mapping_set_version, license;
- prefixes: built-in prefixes not redefined; registry prefixes (carrot, OMOP...)
  not bound to another namespace; every CURIE's prefix declared;
- header: the columns the registry needs, no duplicates;
- every row: the JSON schema, CURIEs, known predicate and justification (the
  vocabularies are curated, so unknown ones are errors), value lengths that fit
  the registry columns, and no repeated assertion (subject, predicate,
  modifier, object, justification), which the database would also reject.

CURIEs are stored in a canonical form: when a file binds the namespace of one
of the registry's prefixes to another name (say ``athena:`` for OMOP's), its
CURIEs are rewritten to the registry's prefix, so the same concept is one Term.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import unquote

# Both ship with apache-airflow-core, so the Airflow image already has them.
import jsonschema
import yaml

from libs.registry_import.full_validate_licenses import LicenseLookup
from libs.registry_import.full_validate_parse import ERROR, WARNING, Issue, ParsedSSSOM
from libs.rules_export.sssom import (
    OMOP_CONCEPT_IRI,
    OMOP_CONCEPT_PREFIX,
    ORCID_IRI,
    ORCID_PREFIX,
    SUBJECT_IRI,
    SUBJECT_PREFIX,
)

SPEC_DIR = Path(__file__).resolve().parent.parent / "sssom_spec"

DRAFT = "DRAFT"
PUBLISHED = "PUBLISHED"

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

# The registry's own prefix names. A file may bind these namespaces to other
# names (CURIEs are rewritten to these), but may not bind these names to other
# namespaces, or e.g. "carrot:x" would mean two different things.
REGISTRY_PREFIXES = {
    **BUILTIN_PREFIXES,
    SUBJECT_PREFIX: SUBJECT_IRI,
    OMOP_CONCEPT_PREFIX: OMOP_CONCEPT_IRI,
    ORCID_PREFIX: ORCID_IRI,
    # used by the seeded predicate oboInOwl:hasDbXref
    "oboInOwl": "http://www.geneontology.org/formats/oboInOwl#",
}
_REGISTRY_PREFIX_BY_NAMESPACE = {ns: p for p, ns in REGISTRY_PREFIXES.items()}

NCNAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]*$")
CURIE = re.compile(r"^(?P<prefix>[A-Za-z_][A-Za-z0-9_.\-]*):(?P<local>.*)$")

# Columns every registry mapping needs. SSSOM itself also allows literal
# mappings (no subject_id/object_id), which the registry can't store: a Mapping
# links two Terms.
REQUIRED_COLUMNS = ("subject_id", "predicate_id", "object_id", "mapping_justification")
# Mapping set slots the registry needs (SSSOM requires only id and license).
REQUIRED_SET_SLOTS = ("mapping_set_id", "mapping_set_version", "license")

# Override keys the API may send (its friendly names and the SSSOM slot names).
OVERRIDE_SLOTS = {
    "set_uri": "mapping_set_id",
    "mapping_set_id": "mapping_set_id",
    "set_version": "mapping_set_version",
    "mapping_set_version": "mapping_set_version",
    "title": "mapping_set_title",
    "mapping_set_title": "mapping_set_title",
    "description": "mapping_set_description",
    "mapping_set_description": "mapping_set_description",
    "license": "license",
}

# Overrides that aren't metadata but change how a Mapper direct publish's file
# is built: include_orcid_ids writes the publishing user's ORCID iD as the
# set's creator_id (off unless the user opted in).
BUILD_OPTIONS = {"include_orcid_ids"}

# Mapping slots stored in Mapping/Term columns. Every other slot in a row
# (standard or extension) goes to Mapping.extra_metadata, so nothing is lost.
PROMOTED_MAPPING_SLOTS = {
    "subject_id",
    "subject_label",
    "subject_type",
    "subject_category",
    "predicate_id",
    "predicate_modifier",
    "object_id",
    "object_label",
    "object_type",
    "object_category",
    "mapping_justification",
    "mapping_cardinality",
    "confidence",
    "author_id",
    "reviewer_id",
    "mapping_date",
    "comment",
    "other",
}
# Mapping set slots stored in MappingSet columns; the rest go to extra_metadata.
PROMOTED_SET_SLOTS = {
    "mapping_set_id",
    "mapping_set_version",
    "mapping_set_title",
    "mapping_set_description",
    "license",
    "creator_id",
    "publication_date",
    "subject_source",
    "subject_source_version",
    "object_source",
    "object_source_version",
    "curie_map",
}
# Set-level slots that apply to every mapping that doesn't set them itself
# (SSSOM "propagatable slots"), for the ones the registry stores per mapping/term.
PROPAGATED_TO_ROWS = (
    "subject_type",
    "object_type",
    "object_source_version",
    "mapping_date",
)

# Column widths in the registry tables (registry/models.py).
MAX_LENGTHS = {
    "set_uri": 500,
    "set_version": 100,
    "title": 500,
    "subject_source": 500,
    "subject_source_version": 255,
    "object_source": 500,
    "object_source_version": 255,
    "canonical_iri": 1000,
    "type": 255,
    "category": 255,
    "prefix": 255,
    "ext_source_field": 255,
    "other": 255,
}

# Order of the values in each staging row (load.STAGING_TABLE has these columns).
STAGING_COLUMNS = (
    "row_no",
    "subject_iri",
    "subject_label",
    "subject_type",
    "subject_category",
    "subject_prefix",
    "subject_ext_level",
    "subject_ext_field",
    "subject_ext_value",
    "predicate_id",
    "predicate_modifier",
    "object_iri",
    "object_label",
    "object_type",
    "object_category",
    "object_prefix",
    "object_source_version",
    "mapping_justification",
    "mapping_cardinality",
    "confidence",
    "author_ids",
    "reviewer_ids",
    "mapping_date",
    "comment",
    "other",
    "extra_metadata",
)


# ---------------------------------------------------------------------------
# The SSSOM specification (vendored)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Spec:
    mapping_slots: frozenset[str]
    set_slots: frozenset[str]
    entity_reference_slots: frozenset[str]
    multivalued_slots: frozenset[str]
    number_slots: frozenset[str]
    # Validators for the Mapping slots whose schema says more than "a string"
    # or "a list of strings" (enums, numbers with a range, dates, patterns).
    slot_validators: dict[str, Any]
    set_validator: Any


def _schema_types(definition: Mapping[str, Any]) -> set[str]:
    if "type" in definition:
        t = definition["type"]
        return {t} if isinstance(t, str) else set(t)
    types: set[str] = set()
    for option in definition.get("anyOf", []):
        types |= _schema_types(option)
    return types


@cache
def load_spec() -> Spec:
    """The vendored SSSOM 1.0 JSON schema and LinkML schema, read once."""
    schema = json.loads((SPEC_DIR / "sssom_schema.schema.json").read_text())
    linkml = yaml.safe_load((SPEC_DIR / "sssom_schema.yaml").read_text())
    mapping_props = schema["$defs"]["Mapping"]["properties"]
    set_props = schema["$defs"]["MappingSet"]["properties"]

    def validator(subschema: Mapping[str, Any]):
        doc = {**subschema, "$defs": schema["$defs"]}
        return jsonschema.Draft201909Validator(
            doc, format_checker=jsonschema.Draft201909Validator.FORMAT_CHECKER
        )

    def is_plain_text(definition: Mapping[str, Any]) -> bool:
        keys = set(definition) - {"description"}
        if keys == {"type"}:
            return definition["type"] == "string"
        if keys == {"type", "items"}:
            return definition["type"] == "array" and definition["items"] == {
                "type": "string"
            }
        return False

    all_props = {**set_props, **mapping_props}
    return Spec(
        mapping_slots=frozenset(mapping_props),
        set_slots=frozenset(set_props) - {"mappings"},
        entity_reference_slots=frozenset(
            name
            for name, slot in linkml["slots"].items()
            if (slot or {}).get("range") == "EntityReference"
        ),
        multivalued_slots=frozenset(
            n for n, d in all_props.items() if "array" in _schema_types(d)
        ),
        number_slots=frozenset(
            n for n, d in all_props.items() if "number" in _schema_types(d)
        ),
        slot_validators={
            name: validator(definition)
            for name, definition in mapping_props.items()
            if not is_plain_text(definition)
        },
        set_validator=validator({"$ref": "#/$defs/MappingSet"}),
    )


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass
class Vocabulary:
    """The registry's controlled vocabularies (predicates, justifications)."""

    predicates: set[str]
    justifications: set[str]


@dataclass
class SetRecord:
    """The registry_mappingset columns that come from the file."""

    set_uri: str = ""
    set_version: str = ""
    title: str = ""
    description: str = ""
    license_id: str | None = None
    sssom_version: str = "1.0"
    creator_ids: list[str] = field(default_factory=list)
    publication_date: date | None = None
    subject_source: str = ""
    subject_source_version: str = ""
    object_source: str = ""
    object_source_version: str = ""
    curie_map: dict[str, str] = field(default_factory=dict)
    extra_metadata: dict[str, Any] = field(default_factory=dict)


class IssueLog:
    """Collects issues, keeping at most ``max_issues`` but counting them all."""

    def __init__(self, max_issues: int):
        self.max_issues = max_issues
        self.items: list[Issue] = []
        self.errors = 0
        self.warnings = 0
        self.dropped = 0

    def add(self, issue: Issue) -> None:
        if issue.level == ERROR:
            self.errors += 1
        else:
            self.warnings += 1
        if len(self.items) < self.max_issues:
            self.items.append(issue)
        else:
            self.dropped += 1

    def error(self, code: str, message: str, line=None, column=None) -> None:
        self.add(Issue(ERROR, code, message, line, column))

    def warning(self, code: str, message: str, line=None, column=None) -> None:
        self.add(Issue(WARNING, code, message, line, column))

    def as_dicts(self) -> list[dict[str, Any]]:
        issues = [i.as_dict() for i in self.items]
        if self.dropped:
            issues.append(
                Issue(
                    WARNING,
                    "issues_truncated",
                    f"{self.dropped} more issues were found but not stored "
                    f"({self.errors} errors and {self.warnings} warnings in all)",
                ).as_dict()
            )
        return issues


@dataclass
class ImportPlan:
    mapping_set: SetRecord
    # one tuple per mapping, values in STAGING_COLUMNS order
    rows: list[tuple]
    issues: IssueLog
    status: str = PUBLISHED

    @property
    def ok(self) -> bool:
        return self.issues.errors == 0

    def summary(self) -> str:
        first = next((i for i in self.issues.items if i.level == ERROR), None)
        text = (
            f"{self.issues.errors} errors, {self.issues.warnings} warnings"
            f" in {len(self.rows)} valid mappings"
        )
        if first:
            where = f" (line {first.line})" if first.line else ""
            text += f". First error{where}: {first.code}: {first.message}"
        return text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _jsonable(value: Any) -> Any:
    """YAML gives dates as date objects; JSON (and the SSSOM schema) want strings."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def normalise_overrides(
    overrides: Mapping[str, Any] | None, log: IssueLog
) -> tuple[dict[str, str], str]:
    """
    The API's metadata overrides as SSSOM slots, and the status to publish with.
    """
    slots: dict[str, str] = {}
    status = PUBLISHED
    for key, value in (overrides or {}).items():
        if value is None or value == "":
            continue
        if key == "status":
            if value not in (DRAFT, PUBLISHED):
                log.error(
                    "invalid_override",
                    f"status must be {DRAFT} or {PUBLISHED}, not {value!r}",
                )
            else:
                status = value
        elif key in OVERRIDE_SLOTS:
            slots[OVERRIDE_SLOTS[key]] = str(value)
        elif key in BUILD_OPTIONS:
            pass  # used when building a Mapper direct publish's file (core.py)
        else:
            log.warning("unknown_override", f"Ignored unknown override {key!r}")
    return slots, status


def _coerce_set_slots(metadata: dict[str, Any], spec: Spec, log: IssueLog) -> None:
    """
    Undo YAML's guessing for slots the schema says are strings or lists, e.g.
    ``mapping_set_version: 1.0`` (a float to YAML) becomes "1.0".
    """
    for slot, value in list(metadata.items()):
        if slot not in spec.set_slots or slot in ("curie_map", "extension_definitions"):
            continue
        if slot in spec.multivalued_slots:
            if not isinstance(value, list):
                metadata[slot] = [value]
                log.warning(
                    "coerced_value",
                    f"Metadata slot {slot!r} is multivalued; read {value!r} as a list",
                    column=slot,
                )
        elif isinstance(value, bool) or (
            isinstance(value, (int, float)) and slot not in spec.number_slots
        ):
            metadata[slot] = str(value)
            log.warning(
                "coerced_value",
                f"Metadata slot {slot!r} should be a string; read {value!r} as "
                f"{str(value)!r}. Quote it in the YAML to be sure of the exact text.",
                column=slot,
            )


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def carrot_term_parts(local: str) -> tuple[str, str, str]:
    """
    (ext_term_level, ext_source_field, ext_source_value) for the local part of
    a carrot:<field>[/<value>] subject, as the SSSOM exporter percent-encodes
    them. Blank when it isn't of that shape.
    """
    field_part, sep, value_part = local.partition("/")
    source_field = unquote(field_part)
    source_value = unquote(value_part)
    if not source_field:
        return "", "", ""
    if sep and source_value:
        return "VALUE", source_field, source_value
    if sep:
        return "", "", ""  # "carrot:field/" has no value: not Carrot-shaped
    return "FIELD", source_field, ""


class _Curies:
    """Checks CURIEs against a file's prefixes and writes them canonically."""

    def __init__(self, curie_map: Mapping[str, str]):
        self.prefixes = {**BUILTIN_PREFIXES, **curie_map}
        self.canonical_prefix = {
            p: _REGISTRY_PREFIX_BY_NAMESPACE.get(ns, p)
            for p, ns in self.prefixes.items()
        }

    def resolve(self, value: str) -> tuple[str | None, str, str]:
        """
        (canonical CURIE, its prefix, its local part), or (None, reason, "")
        when ``value`` isn't a CURIE with a declared prefix.
        """
        m = CURIE.match(value)
        if not m or m["local"].startswith("//"):
            return None, f"{value!r} is not a CURIE (prefix:local_id)", ""
        prefix = m["prefix"]
        if prefix not in self.prefixes:
            return None, f"prefix {prefix!r} of {value!r} is not in the curie_map", ""
        canonical = self.canonical_prefix[prefix]
        return f"{canonical}:{m['local']}", canonical, m["local"]


# ---------------------------------------------------------------------------
# Set level
# ---------------------------------------------------------------------------


def _check_set(
    parsed: ParsedSSSOM,
    override_slots: dict[str, str],
    spec: Spec,
    licenses: LicenseLookup,
    log: IssueLog,
) -> tuple[SetRecord, dict[str, Any], set[str], _Curies] | None:
    """
    Check the metadata block (with the overrides applied). Returns the set's
    columns, the values propagated to rows, the declared extension slots and the
    CURIE resolver; None when the prefixes are unusable.
    """
    metadata = dict(parsed.metadata)

    for slot, value in override_slots.items():
        current = metadata.get(slot)
        if current not in (None, "") and str(current) != value:
            log.warning(
                "metadata_overridden",
                f"{slot} {current!r} in the file was replaced by {value!r} "
                "from the request",
                column=slot,
            )
        metadata[slot] = value

    _coerce_set_slots(metadata, spec, log)

    # Extension slots (spec-model.md, "Non-standard slots")
    extension_slots: set[str] = set()
    ext_defs = metadata.get("extension_definitions") or []
    if not isinstance(ext_defs, list):
        log.error(
            "invalid_extension_definition",
            "extension_definitions must be a list",
            column="extension_definitions",
        )
        ext_defs = []
    for definition in ext_defs:
        name = definition.get("slot_name") if isinstance(definition, dict) else None
        if not name or not NCNAME.match(str(name)):
            log.error(
                "invalid_extension_definition",
                f"Extension slot name {name!r} is not a valid name",
                column="extension_definitions",
            )
        elif name in spec.mapping_slots | spec.set_slots:
            log.error(
                "invalid_extension_definition",
                f"Extension slot {name!r} clashes with a standard SSSOM slot",
                column="extension_definitions",
            )
        else:
            extension_slots.add(name)

    for key in metadata:
        if key not in spec.set_slots and key not in extension_slots:
            log.warning(
                "unknown_metadata_key",
                f"Metadata key {key!r} is not an SSSOM slot or a declared "
                "extension; it is kept in extra_metadata",
                column=key,
            )

    # Prefixes
    curie_map = metadata.get("curie_map") or {}
    if not isinstance(curie_map, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in curie_map.items()
    ):
        log.error(
            "invalid_curie_map",
            "curie_map must map prefix names to namespace IRIs",
            column="curie_map",
        )
        return None
    usable = True
    for prefix, namespace in curie_map.items():
        if not NCNAME.match(prefix):
            log.error(
                "invalid_curie_map",
                f"Prefix {prefix!r} is not a valid prefix name",
                column="curie_map",
            )
            usable = False
        elif prefix in BUILTIN_PREFIXES and namespace != BUILTIN_PREFIXES[prefix]:
            log.error(
                "builtin_prefix_redefined",
                f"Built-in prefix {prefix!r} must not be redefined (as {namespace!r})",
                column="curie_map",
            )
            usable = False
        elif prefix in REGISTRY_PREFIXES and namespace != REGISTRY_PREFIXES[prefix]:
            log.error(
                "prefix_conflict",
                f"Prefix {prefix!r} is bound to {REGISTRY_PREFIXES[prefix]!r} in "
                f"the registry, but to {namespace!r} in this file",
                column="curie_map",
            )
            usable = False
    if not usable:
        return None
    curies = _Curies(curie_map)

    # The official JSON schema, for the set-level slots
    document = {
        k: _jsonable(v)
        for k, v in metadata.items()
        if k in spec.set_slots and k != "extension_definitions"
    }
    for error in spec.set_validator.iter_errors(document):
        column = str(error.absolute_path[0]) if error.absolute_path else None
        log.error(
            "schema_violation",
            f"Metadata: {error.message[:300]}",
            column=column,
        )

    for slot in REQUIRED_SET_SLOTS:
        if metadata.get(slot) in (None, ""):
            log.error(
                "missing_metadata_slot",
                f"{slot} is required, in the file or in the request",
                column=slot,
            )

    for slot in spec.entity_reference_slots & set(metadata):
        values = metadata[slot]
        for value in values if isinstance(values, list) else [values]:
            resolved, reason, _ = curies.resolve(str(value))
            if resolved is None:
                log.error("invalid_curie", f"Metadata {slot}: {reason}", column=slot)

    # The set's columns
    record = SetRecord(curie_map=dict(curie_map))
    record.set_uri = str(metadata.get("mapping_set_id") or "")
    record.set_version = str(metadata.get("mapping_set_version") or "")
    record.title = str(metadata.get("mapping_set_title") or "")
    if not record.title and record.set_uri:
        record.title = record.set_uri
        log.warning(
            "missing_title",
            "No mapping_set_title; the mapping_set_id is used as the title",
            column="mapping_set_title",
        )
    record.description = str(metadata.get("mapping_set_description") or "")
    record.sssom_version = str(metadata.get("sssom_version") or "1.0")
    creator_ids = metadata.get("creator_id") or []
    record.creator_ids = [str(c) for c in creator_ids]
    if metadata.get("publication_date") not in (None, ""):
        record.publication_date = _parse_date(metadata["publication_date"])
    for slot in (
        "subject_source",
        "subject_source_version",
        "object_source",
        "object_source_version",
    ):
        setattr(record, slot, str(metadata.get(slot) or ""))

    license_iri = metadata.get("license")
    license = licenses.find(license_iri)
    record.license_id = license.id if license else None
    if license_iri and license is None:
        log.warning(
            "unknown_license",
            f"License {license_iri!r} is not one of the registry's licenses; "
            "the set is stored without a license link (the IRI is kept in "
            "extra_metadata)",
            column="license",
        )
    elif license and license.is_deprecated:
        log.warning(
            "deprecated_license",
            f"License {license_iri!r} ({record.license_id}) is deprecated by SPDX",
            column="license",
        )

    record.extra_metadata = {
        k: _jsonable(v) for k, v in metadata.items() if k not in PROMOTED_SET_SLOTS
    }
    if license_iri and record.license_id is None:
        record.extra_metadata["license"] = str(license_iri)

    for name, value in (
        ("set_uri", record.set_uri),
        ("set_version", record.set_version),
        ("title", record.title),
        ("subject_source", record.subject_source),
        ("subject_source_version", record.subject_source_version),
        ("object_source", record.object_source),
        ("object_source_version", record.object_source_version),
    ):
        if len(value) > MAX_LENGTHS[name]:
            log.error(
                "value_too_long",
                f"{name} is {len(value)} characters; the registry allows "
                f"{MAX_LENGTHS[name]}",
                column=name,
            )

    propagated = {
        slot: _jsonable(metadata[slot])
        for slot in PROPAGATED_TO_ROWS
        if metadata.get(slot) not in (None, "")
    }
    return record, propagated, extension_slots, curies


# ---------------------------------------------------------------------------
# Rows
# ---------------------------------------------------------------------------


def _check_header(
    header: list[str], spec: Spec, ext_slots: set[str], log: IssueLog
) -> bool:
    ok = True
    seen: set[str] = set()
    for column in header:
        if column in seen:
            log.error(
                "duplicate_column",
                f"Column {column!r} appears twice",
                line=None,
                column=column,
            )
            ok = False
        seen.add(column)
        if column not in spec.mapping_slots and column not in ext_slots:
            log.warning(
                "unknown_column",
                f"Column {column!r} is not an SSSOM slot or a declared extension; "
                "its values are kept in extra_metadata",
                column=column,
            )
    for column in REQUIRED_COLUMNS:
        if column not in seen:
            log.error(
                "missing_column",
                f"Required column {column!r} is missing",
                column=column,
            )
            ok = False
    return ok


def _slot_errors(spec: Spec, slot: str, value: Any, cache: dict) -> tuple[str, ...]:
    """Schema errors for one slot value, memoised: most values repeat."""
    key = (slot, tuple(value) if isinstance(value, list) else value)
    if key not in cache:
        cache[key] = tuple(
            e.message[:300] for e in spec.slot_validators[slot].iter_errors(value)
        )
    return cache[key]


def build_import(
    parsed: ParsedSSSOM,
    vocab: Vocabulary,
    licenses: LicenseLookup,
    overrides: Mapping[str, Any] | None = None,
    max_issues: int = 1000,
) -> ImportPlan:
    """
    Validate a parsed SSSOM file and normalise it for loading. ``overrides``
    are the request's metadata (license as an IRI, see helpers.file_overrides).
    """
    spec = load_spec()
    log = IssueLog(max_issues)
    for issue in parsed.issues:
        log.add(issue)
    override_slots, status = normalise_overrides(overrides, log)
    plan = ImportPlan(SetRecord(), [], log, status)
    if not parsed.header:
        return plan

    checked = _check_set(parsed, override_slots, spec, licenses, log)
    if checked is None:
        return plan
    plan.mapping_set, propagated, ext_slots, curies = checked
    if not _check_header(parsed.header, spec, ext_slots, log):
        return plan

    header = parsed.header
    width = len(header)
    seen: dict[tuple, int] = {}
    cache: dict = {}
    for line, values in parsed.rows:
        if len(values) != width:
            log.error(
                "row_length",
                f"Row has {len(values)} values; the header has {width} columns",
                line=line,
            )
            continue
        row = _check_row(
            line,
            dict(zip(header, values)),
            spec,
            vocab,
            curies,
            ext_slots,
            propagated,
            log,
            cache,
        )
        if row is None:
            continue
        key = (row[1], row[9], row[10], row[11], row[17])
        if key in seen:
            log.error(
                "duplicate_mapping",
                "Same subject, predicate, predicate_modifier, object and "
                f"mapping_justification as line {seen[key]}",
                line=line,
            )
            continue
        seen[key] = line
        plan.rows.append(row)

    if not parsed.rows:
        log.error("no_mappings", "File contains no mappings")
    return plan


def _check_row(
    line: int,
    raw: dict[str, str],
    spec: Spec,
    vocab: Vocabulary,
    curies: _Curies,
    ext_slots: set[str],
    propagated: dict[str, Any],
    log: IssueLog,
    cache: dict,
) -> tuple | None:
    """One staging row (STAGING_COLUMNS order), or None if the row has errors."""
    errors_before = log.errors

    # Typed values, as the JSON schema expects them
    typed: dict[str, Any] = {}
    extra: dict[str, Any] = {}
    for column, value in raw.items():
        if value == "":
            continue
        if column not in spec.mapping_slots:
            extra[column] = value  # extension or unknown column, kept verbatim
            continue
        if column in spec.multivalued_slots:
            typed[column] = value.split("|")
        elif column in spec.number_slots:
            try:
                typed[column] = float(value)
            except ValueError:
                log.error(
                    "invalid_number",
                    f"{column} {value!r} is not a number",
                    line,
                    column,
                )
                continue
        else:
            typed[column] = value

    for column in REQUIRED_COLUMNS:
        if column not in typed:
            message = f"{column} is empty"
            if column in ("subject_id", "object_id"):
                message += " (literal mappings are not supported by the registry)"
            log.error("missing_value", message, line, column)
    if log.errors > errors_before:
        return None

    # The official JSON schema, slot by slot. That is the whole Mapping schema
    # here: its other rules (allOf/if) are about literal mappings, which are
    # rejected above and below, and unknown columns never reach ``typed``.
    for column, value in typed.items():
        if column in spec.slot_validators:
            for message in _slot_errors(spec, column, value, cache):
                log.error("schema_violation", f"{column}: {message}", line, column)
    for side in ("subject", "object"):
        if typed.get(f"{side}_type") == "rdfs literal":
            log.error(
                "missing_value",
                f"{side}_type is 'rdfs literal': literal mappings are not "
                "supported by the registry",
                line,
                f"{side}_type",
            )

    # CURIEs, written canonically
    for column in spec.entity_reference_slots & set(typed):
        values = typed[column] if isinstance(typed[column], list) else [typed[column]]
        canonical = []
        for value in values:
            resolved, reason, _ = curies.resolve(value)
            if resolved is None:
                code = "undeclared_prefix" if "curie_map" in reason else "invalid_curie"
                log.error(code, reason, line, column)
            canonical.append(resolved)
        if log.errors == errors_before:
            typed[column] = (
                canonical if isinstance(typed[column], list) else canonical[0]
            )
    if log.errors > errors_before:
        return None

    predicate = typed["predicate_id"]
    if predicate not in vocab.predicates:
        log.error(
            "unknown_predicate",
            f"Predicate {predicate!r} is not in the registry's predicate vocabulary",
            line,
            "predicate_id",
        )
    justification = typed["mapping_justification"]
    if justification not in vocab.justifications:
        log.error(
            "unknown_justification",
            f"Justification {justification!r} is not in the registry's "
            "justification vocabulary",
            line,
            "mapping_justification",
        )

    # Propagated set-level values fill the gaps
    for slot, value in propagated.items():
        typed.setdefault(slot, value)
    mapping_date = None
    if "mapping_date" in typed:
        mapping_date = _parse_date(typed["mapping_date"])
        if mapping_date is None:
            log.error(
                "invalid_date",
                f"mapping_date {typed['mapping_date']!r} is not a date",
                line,
                "mapping_date",
            )

    subject_iri, subject_prefix, subject_local = curies.resolve(raw["subject_id"])
    object_iri, object_prefix, _ = curies.resolve(raw["object_id"])
    ext_level = ext_field = ext_value = ""
    if subject_prefix == SUBJECT_PREFIX:
        ext_level, ext_field, ext_value = carrot_term_parts(subject_local)

    lengths = {
        "canonical_iri": max(len(subject_iri or ""), len(object_iri or "")),
        "type": max(
            len(typed.get("subject_type", "")), len(typed.get("object_type", ""))
        ),
        "category": max(
            len(typed.get("subject_category", "")),
            len(typed.get("object_category", "")),
        ),
        "prefix": max(len(subject_prefix), len(object_prefix)),
        "object_source_version": len(str(typed.get("object_source_version", ""))),
        "ext_source_field": len(ext_field),
        "other": len(typed.get("other", "")),
    }
    for name, length in lengths.items():
        if length > MAX_LENGTHS[name]:
            log.error(
                "value_too_long",
                f"{name} is {length} characters; the registry allows {MAX_LENGTHS[name]}",
                line,
                name,
            )

    if log.errors > errors_before:
        return None

    for column, value in typed.items():
        if column not in PROMOTED_MAPPING_SLOTS and column in raw and raw[column] != "":
            extra[column] = value
    return (
        line,
        subject_iri,
        typed.get("subject_label", ""),
        typed.get("subject_type", ""),
        typed.get("subject_category", ""),
        subject_prefix,
        ext_level,
        ext_field,
        ext_value,
        predicate,
        typed.get("predicate_modifier", ""),
        object_iri,
        typed.get("object_label", ""),
        typed.get("object_type", ""),
        typed.get("object_category", ""),
        object_prefix,
        str(typed.get("object_source_version", "")),
        justification,
        typed.get("mapping_cardinality", ""),
        typed.get("confidence"),
        json.dumps(typed.get("author_id", [])),
        json.dumps(typed.get("reviewer_id", [])),
        mapping_date,
        typed.get("comment", ""),
        typed.get("other") or None,
        json.dumps(extra, ensure_ascii=False),
    )

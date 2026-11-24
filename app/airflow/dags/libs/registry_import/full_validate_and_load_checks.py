"""
Full validation of an SSSOM file for the registry, and its normalisation into
an ImportPlan: the mapping set's columns plus one staging row per mapping, in
exactly the shape full_validate_and_load_db.py writes. Validation and normalisation are one pass, so
what is accepted is precisely what is loaded.

Checks, each reported as an Issue (see parse.Issue):

- metadata: the official SSSOM 1.0 JSON schema (vendored in libs/sssom_spec),
  plus what the registry needs: mapping_set_id, mapping_set_version (SemVer or
  an ISO date, see set_versions.py), license;
- prefixes: built-in prefixes not redefined; reserved prefixes (carrot, OMOP...)
  not bound to another namespace; every CURIE's prefix declared, and not a name
  the registry already uses for another namespace;
- header: the columns the registry needs, no duplicates;
- every row: the JSON schema, CURIEs, known predicate and justification (the
  vocabularies are curated, so unknown ones are errors), value lengths that fit
  the registry columns, and no repeated assertion (subject, predicate,
  modifier, object, justification), which the database would also reject.

CURIEs are stored in a canonical form, with the registry's prefix names
(registry_prefix): each name stands for one namespace and each namespace has one
name. When a file binds a known namespace to another name (say ``athena:`` for
OMOP's), its CURIEs are rewritten to the registry's name, so the same concept is
one Term. A namespace the registry hasn't seen keeps the file's name, which the
load registers; a name the registry already uses for another namespace is an
error, as it would make one CURIE mean two things.

Whether the set may be added to (check_set_version_is_new, check_set_owner)
depends on the registry's other sets, which the caller looks up.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

# Both ship with apache-airflow-core, so the Airflow image already has them.
import jsonschema
import yaml

from libs.registry_import.full_validate_and_load_parse import (
    ERROR,
    WARNING,
    Issue,
    ParsedSSSOM,
)
from libs.registry_import.set_versions import (
    FORMAT_HINT,
    set_version_error,
    version_key,
)
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
# registry_origin ids (helpers.py has them too, but imports this module)
CARROT_DIRECT_PUBLISH = "CARROT_DIRECT_PUBLISH"

# The API's registry.models.CARROT_MAPPING_SET_NAMESPACE: Carrot set ids are
# {namespace}{uuid}, and their series has that uuid as its id (series_id_for).
CARROT_MAPPING_SET_NAMESPACE = "https://carrot.ac.uk/registry/mapping-sets/"

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

# The registry's reserved prefix names (also seeded in registry_prefix). A file
# may bind these namespaces to other names (CURIEs are rewritten to these), but
# may not bind these names to other namespaces, or e.g. "carrot:x" would mean
# two different things: the whole file is rejected. Other registered names are
# checked per CURIE (see _Curies).
REGISTRY_PREFIXES = {
    **BUILTIN_PREFIXES,
    SUBJECT_PREFIX: SUBJECT_IRI,
    OMOP_CONCEPT_PREFIX: OMOP_CONCEPT_IRI,
    ORCID_PREFIX: ORCID_IRI,
    # used by the seeded predicate oboInOwl:hasDbXref
    "oboInOwl": "http://www.geneontology.org/formats/oboInOwl#",
}

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
# is built: include_author_orcid_ids writes the ORCID iD of each mapping's
# author as its author_id (off unless the user opted in).
BUILD_OPTIONS = {"include_author_orcid_ids"}

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
    "namespace": 1000,
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
    # registry_prefix: prefix name -> namespace
    prefixes: dict[str, str] = field(default_factory=dict)


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
    # The canonical prefixes the rows' terms use (name -> namespace), which the
    # load registers in registry_prefix.
    prefixes: dict[str, str] = field(default_factory=dict)

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


def _is_http_iri(value: str) -> bool:
    """An absolute http(s) IRI with a host and no whitespace."""
    if any(c.isspace() for c in value):
        return False
    parts = urlsplit(value)
    return parts.scheme in ("http", "https") and bool(parts.netloc)


class _Curies:
    """
    Checks CURIEs against a file's prefixes and writes them canonically, with
    the registry's name for each namespace (``registered``: name -> namespace,
    the reserved prefixes and registry_prefix).
    """

    def __init__(self, curie_map: Mapping[str, str], registered: Mapping[str, str]):
        self.prefixes = {**BUILTIN_PREFIXES, **curie_map}
        name_of = {ns: p for p, ns in registered.items()}
        # file prefix -> canonical prefix, and canonical prefix -> namespace
        self.canonical_prefix: dict[str, str] = {}
        self.namespaces: dict[str, str] = {}
        # file prefix -> why its CURIEs can't be stored
        self.conflicts: dict[str, str] = {}
        for prefix, namespace in self.prefixes.items():
            if namespace in name_of:
                canonical = name_of[namespace]
            elif prefix in registered:
                self.conflicts[prefix] = (
                    f"prefix {prefix!r} is already used in the registry for "
                    f"{registered[prefix]!r}, but this file binds it to "
                    f"{namespace!r}; give that namespace another prefix name"
                )
                continue
            else:
                # New to the registry: the file's first name for it
                canonical = prefix
                name_of[namespace] = prefix
            self.canonical_prefix[prefix] = canonical
            self.namespaces[canonical] = namespace

    def resolve(self, value: str) -> tuple[str | None, str, str]:
        """
        (canonical CURIE, its prefix, its local part), or (None, reason, issue
        code) when ``value`` can't be stored as a CURIE.
        """
        m = CURIE.match(value)
        if not m or m["local"].startswith("//"):
            return (
                None,
                f"{value!r} is not a CURIE (prefix:local_id)",
                "invalid_curie",
            )
        prefix = m["prefix"]
        if prefix in self.conflicts:
            return None, f"{value!r}: {self.conflicts[prefix]}", "prefix_conflict"
        if prefix not in self.prefixes:
            return (
                None,
                f"prefix {prefix!r} of {value!r} is not in the curie_map",
                "undeclared_prefix",
            )
        canonical = self.canonical_prefix[prefix]
        return f"{canonical}:{m['local']}", canonical, m["local"]


# ---------------------------------------------------------------------------
# Set level
# ---------------------------------------------------------------------------


def resolve_set_uri(
    file_id: str,
    request_id: str | None,
    series_set_uri: str | None,
    log: IssueLog,
) -> str:
    """
    The set_uri a file's mapping set is stored under, from its mapping_set_id
    (``file_id``), the request's set_uri override (``request_id``) and the
    set_uri of the existing series the request adds a version to
    (``series_set_uri``).

    The file and the request may not disagree, since the stored file is served
    as-is: an id in the file must match the request's. A file without one takes
    the request's, or a new Carrot set id, so the raw file has no id (warned).
    """
    requested = {r for r in (request_id, series_set_uri) if r}
    if len(requested) > 1:
        log.error(
            "mapping_set_id_mismatch",
            f"The request's set_uri {request_id!r} is not the set_uri of the "
            f"mapping set it adds a version to ({series_set_uri!r})",
            column="mapping_set_id",
        )
    requested_id = series_set_uri or request_id
    if file_id:
        if requested_id and requested_id != file_id:
            log.error(
                "mapping_set_id_mismatch",
                f"mapping_set_id {file_id!r} in the file is not the request's "
                f"{requested_id!r}; the file and the request must agree",
                column="mapping_set_id",
            )
        return file_id
    set_uri = requested_id or f"{CARROT_MAPPING_SET_NAMESPACE}{uuid.uuid4()}"
    log.warning(
        "mapping_set_id_not_in_file",
        f"The file has no mapping_set_id; the set is stored as {set_uri!r}, "
        "but the downloadable file stays without one",
        column="mapping_set_id",
    )
    return set_uri


_LICENSE_IRI_SUFFIX = re.compile(r"(/legalcode(\.[a-z-]+)?|\.html|\.json|\.txt)$")


def license_iri_key(iri: str) -> str:
    """
    A license IRI as compared with the registry's: case, scheme, ``www.``, a
    trailing slash and the page suffixes (``/legalcode``, ``.html``...) are
    ignored, so https://creativecommons.org/licenses/by/4.0/ is
    http://creativecommons.org/licenses/by/4.0/legalcode.
    """
    key = iri.strip().lower()
    key = re.sub(r"^https?://(www\.)?", "", key).rstrip("/")
    return _LICENSE_IRI_SUFFIX.sub("", key).rstrip("/")


@dataclass(frozen=True)
class LicenseRow:
    """A registry_license row: its id and the IRIs it is known by."""

    id: str
    license_iri: str
    see_also: tuple[str, ...] = ()
    is_deprecated: bool = False


def match_license(iri: str, licenses: list[LicenseRow]) -> str | None:
    """
    The License a file's license IRI stands for: one whose license_iri or a
    see_also IRI is that IRI, preferring an exact license_iri, then an exact
    see_also, then the same IRI up to license_iri_key, and a License SPDX
    hasn't deprecated; None if there is none.
    """
    if not iri:
        return None
    key = license_iri_key(iri)
    best: tuple | None = None
    for row in licenses:
        if row.license_iri == iri:
            rank = 0
        elif iri in row.see_also:
            rank = 1
        elif license_iri_key(row.license_iri) == key:
            rank = 2
        elif any(license_iri_key(alias) == key for alias in row.see_also):
            rank = 3
        else:
            continue
        candidate = (rank, row.is_deprecated, row.id)
        if best is None or candidate < best:
            best = candidate
    return best[2] if best else None


def resolve_license(
    file_iri: str,
    file_license_id: str | None,
    license_id: str | None,
    license_iri: str | None,
    log: IssueLog,
) -> tuple[str | None, str]:
    """
    The License the set is linked to and the license IRI it records, from the
    file's license (``file_iri``, and the License it stands for,
    ``file_license_id``) and the request's License (``license_id``, whose IRI is
    ``license_iri``).

    Licences are compared as License ids, so an alias IRI (a License's
    see_also) matches. The file and the request may not disagree, since the
    stored file is served as-is. A file without a license takes the request's,
    so the raw file has none (warned); a license the registry doesn't know is
    kept unlinked (warned), unless the request named one.
    """
    if not file_iri:
        if license_id:
            log.warning(
                "license_not_in_file",
                f"The file has no license; the set is linked to {license_id}, "
                "the request's, but the downloadable file stays without one",
                column="license",
            )
            return license_id, license_iri or ""
        return None, ""  # missing_metadata_slot
    if license_id and file_license_id != license_id:
        found = (
            f"which is {file_license_id}"
            if file_license_id
            else "which isn't a license the registry knows"
        )
        log.error(
            "license_mismatch",
            f"The file's license {file_iri!r} ({found}) is not the request's "
            f"{license_id}; the file and the request must agree",
            column="license",
        )
        return None, file_iri
    if file_license_id is None:
        log.warning(
            "unknown_license",
            f"The file's license {file_iri!r} isn't a license the registry "
            "knows, so the set isn't linked to one; the IRI is kept in "
            "extra_metadata",
            column="license",
        )
    return file_license_id, file_iri


def _check_set(
    parsed: ParsedSSSOM,
    override_slots: dict[str, str],
    spec: Spec,
    license_id: str | None,
    registered_prefixes: Mapping[str, str],
    log: IssueLog,
    series_set_uri: str | None = None,
    file_license_id: str | None = None,
) -> tuple[SetRecord, dict[str, Any], set[str], _Curies] | None:
    """
    Check the metadata block (with the overrides applied). Returns the set's
    columns, the values propagated to rows, the declared extension slots and the
    CURIE resolver; None when the prefixes are unusable.
    """
    metadata = dict(parsed.metadata)

    override_slots = dict(override_slots)
    file_id = metadata.get("mapping_set_id")
    metadata["mapping_set_id"] = resolve_set_uri(
        "" if file_id is None else str(file_id),
        override_slots.pop("mapping_set_id", None),
        series_set_uri,
        log,
    )
    file_iri = metadata.pop("license", None)
    linked_license_id, license_iri = resolve_license(
        "" if file_iri is None else str(file_iri),
        file_license_id,
        license_id,
        override_slots.pop("license", None),
        log,
    )
    if license_iri:
        metadata["license"] = license_iri

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
        elif not _is_http_iri(namespace):
            log.error(
                "invalid_namespace",
                f"Namespace {namespace!r} of prefix {prefix!r} is not an "
                "absolute http(s) IRI",
                column="curie_map",
            )
            usable = False
        if len(namespace) > MAX_LENGTHS["namespace"]:
            log.error(
                "value_too_long",
                f"Namespace of prefix {prefix!r} is {len(namespace)} characters; "
                f"the registry allows {MAX_LENGTHS['namespace']}",
                column="curie_map",
            )
            usable = False
    if not usable:
        return None
    curies = _Curies(curie_map, {**registered_prefixes, **REGISTRY_PREFIXES})

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
            resolved, reason, code = curies.resolve(str(value))
            if resolved is None:
                log.error(code, f"Metadata {slot}: {reason}", column=slot)

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

    # See resolve_license: an IRI not linked to a License is kept.
    record.license_id = linked_license_id
    record.extra_metadata = {
        k: _jsonable(v) for k, v in metadata.items() if k not in PROMOTED_SET_SLOTS
    }
    if license_iri and record.license_id is None:
        record.extra_metadata["license"] = license_iri

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
    if record.set_version and version_key(record.set_version) is None:
        log.error(
            "invalid_set_version",
            f"mapping_set_version {record.set_version!r} must be {FORMAT_HINT}",
            column="mapping_set_version",
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


def check_set_version_is_newer(plan: ImportPlan, existing_versions: list[str]) -> None:
    """
    Sets are immutable: corrections are a new mapping_set_version, higher than
    every version of the set_uri from other imports (``existing_versions``,
    looked up by the caller). A malformed version is reported by build_import.
    """
    record = plan.mapping_set
    if version_key(record.set_version) is None:
        return
    error = set_version_error(record.set_version, existing_versions)
    if error:
        code, message = error
        plan.issues.error(
            code,
            f"Mapping set {record.set_uri}: {message}",
            column="mapping_set_version",
        )


@dataclass(frozen=True)
class SetOwner:
    """Who owns a set: its registry_mappingsetseries row (looked up by the caller)."""

    source_scan_report_id: int | None
    publisher_id: int | None


def set_owner_error(
    owner: SetOwner | None,
    *,
    origin: str,
    scan_report_id: int | None,
    user_id: int | None,
) -> str | None:
    """
    Why this import may not add a version to its set_uri, or None if it may.

    The set's owner decides: a set created by a scan report's publish may only
    get versions from the same scan report (whose permissions the API checks),
    and an uploaded set only from the same user.
    """
    if owner is None:
        return None
    if origin == CARROT_DIRECT_PUBLISH:
        if owner.source_scan_report_id is not None and (
            owner.source_scan_report_id == scan_report_id
        ):
            return None
        return "it was not published from this scan report"
    if owner.publisher_id is not None and owner.publisher_id == user_id:
        return None
    return "it was published by another user"


def check_set_owner(plan: ImportPlan, error: str | None) -> None:
    """An error if ``error`` (from set_owner_error) says the set_uri isn't ours."""
    if error is None:
        return
    plan.issues.error(
        "set_uri_not_owned",
        f"Mapping set {plan.mapping_set.set_uri} already exists and {error}; "
        "only its publisher can add versions. Use another mapping_set_id",
        column="mapping_set_id",
    )


def series_id_for(set_uri: str) -> str:
    """
    The id of a new series for ``set_uri``: the uuid a Carrot set_uri ends
    with, else a random one (the API's registry.models.series_id_for). It is
    the set's page URL, so a Carrot set_uri opens as a link.
    """
    if set_uri.startswith(CARROT_MAPPING_SET_NAMESPACE):
        try:
            return str(
                uuid.UUID(set_uri[len(CARROT_MAPPING_SET_NAMESPACE) :].strip("/"))
            )
        except ValueError:
            pass
    return str(uuid.uuid4())


def set_uri_uuid(set_uri: str) -> str | None:
    """
    The UUID a set_uri ends with, if any. Carrot gives a scan report's sets the
    id {namespace}{ScanReport.uuid} (the API's scan_report_set_uri), the same
    namespace on every Carrot instance, so the UUID is what tells them apart.
    """
    last = set_uri.rstrip("/").rsplit("/", 1)[-1]
    try:
        return str(uuid.UUID(last))
    except ValueError:
        return None


def check_set_uri_not_reserved(
    plan: ImportPlan, origin: str, local_scan_report_id: int | None
) -> None:
    """
    An error if an upload uses the set id of a scan report on this instance
    (``local_scan_report_id``, looked up by the caller from set_uri_uuid).

    Those sets come in by direct publish, which checks the scan report's
    permissions; an upload of one (say from its SSSOM export) would own the set
    and block the scan report's own publishes. Sets of scan reports on other
    Carrot instances (a TRE's export) may still be uploaded.
    """
    if origin == CARROT_DIRECT_PUBLISH or local_scan_report_id is None:
        return
    plan.issues.error(
        "set_uri_reserved",
        f"Mapping set {plan.mapping_set.set_uri} belongs to a scan report on "
        "this Carrot instance; publish it from the scan report instead of "
        "uploading it",
        column="mapping_set_id",
    )


def build_import(
    parsed: ParsedSSSOM,
    vocab: Vocabulary,
    overrides: Mapping[str, Any] | None = None,
    license_id: str | None = None,
    max_issues: int = 1000,
    series_set_uri: str | None = None,
    file_license_id: str | None = None,
) -> ImportPlan:
    """
    Validate a parsed SSSOM file and normalise it for loading. ``overrides``
    are the request's metadata (license as an IRI, see helpers.file_overrides);
    ``license_id`` is the request's License id and ``file_license_id`` the
    License the file's license IRI stands for (see resolve_license);
    ``series_set_uri`` is the set_uri of the existing set the request adds a
    version to (see resolve_set_uri).
    """
    spec = load_spec()
    log = IssueLog(max_issues)
    for issue in parsed.issues:
        log.add(issue)
    override_slots, status = normalise_overrides(overrides, log)
    plan = ImportPlan(SetRecord(), [], log, status)
    if not parsed.header:
        return plan

    checked = _check_set(
        parsed,
        override_slots,
        spec,
        license_id,
        vocab.prefixes,
        log,
        series_set_uri=series_set_uri,
        file_license_id=file_license_id,
    )
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
        for prefix in (row[5], row[15]):
            plan.prefixes[prefix] = curies.namespaces[prefix]

    if not parsed.rows:
        log.error("no_mappings", "File contains no mappings")
    # Stored CURIEs use the registry's names, which may differ from the file's
    # (SNOMED:1 stored as snomed:1), so the stored curie_map declares those too
    # and every stored CURIE expands from its set's metadata. The file's own
    # names are kept, except that the registry's binding wins where a name
    # clashes: that is only possible for a file prefix no row uses, as a used
    # one fails with prefix_conflict, so no stored CURIE needs the file's.
    plan.mapping_set.curie_map.update(plan.prefixes)
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
            resolved, reason, code = curies.resolve(value)
            if resolved is None:
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
        typed.get("other", ""),
        json.dumps(extra, ensure_ascii=False),
    )

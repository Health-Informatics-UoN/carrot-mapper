"""
Quick validation of an uploaded SSSOM/TSV file, run inside the request.

This gives fast feedback on the mistakes people actually make, reading the
metadata block and only the first rows. The registry_import DAG still checks
every row against the SSSOM schema: an error here is always an error there
(apart from the upload limits below and YAML aliases), but a file that passes
here can still fail there. The rules and issue codes follow the DAG's
``libs/registry_import/full_validate_and_load_checks.py``, which this API cannot
import, so keep the two in step.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date
from functools import reduce
from operator import or_
from typing import Any
from urllib.parse import urlsplit

import yaml
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Q
from mapping.models import ScanReport

from registry.models import (
    ImportJob,
    ImportJobStatus,
    License,
    MappingJustification,
    MappingSet,
    Predicate,
    Prefix,
)

ERROR = "error"
WARNING = "warning"

# How many mapping rows are checked here; the DAG checks them all.
MAX_SAMPLE_ROWS = 1000
MAX_ISSUES = 200
# YAML is slow to parse, so a metadata block can't be as large as the file.
MAX_METADATA_BYTES = 1024 * 1024
ALLOWED_EXTENSIONS = (".sssom.tsv", ".tsv")

# Problems with the set's identity rather than the file's content: HTTP 409.
CONFLICT_CODES = frozenset(
    {
        "set_uri_not_owned",
        "set_uri_reserved",
        "set_version_exists",
        "set_version_not_newer",
        "set_version_scheme_mismatch",
        "version_in_flight",
    }
)

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
RESERVED_PREFIXES = {
    **BUILTIN_PREFIXES,
    "carrot": "https://carrot.ac.uk/registry/terms/",
    "OMOP": "https://athena.ohdsi.org/search-terms/terms/",
    "orcid": "https://orcid.org/",
    "oboInOwl": "http://www.geneontology.org/formats/oboInOwl#",
}

# Set versions, as in the DAG's libs/registry_import/set_versions.py: SemVer or
# an ISO date, the same scheme for every version of a set_uri, each new version
# higher than all the others.
_SEMVER = re.compile(r"(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})")
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
VERSION_FORMAT_HINT = (
    "SemVer MAJOR.MINOR.PATCH (e.g. 1.0.0) or an ISO date (YYYY-MM-DD)"
)

NCNAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]*$")
CURIE = re.compile(r"^(?P<prefix>[A-Za-z_][A-Za-z0-9_.\-]*):(?P<local>.*)$")

REQUIRED_COLUMNS = ("subject_id", "predicate_id", "object_id", "mapping_justification")
REQUIRED_SET_SLOTS = ("mapping_set_id", "mapping_set_version", "license")
CURIE_COLUMNS = ("subject_id", "predicate_id", "object_id", "mapping_justification")
# The Mapping slots of the SSSOM 1.0 schema: other columns get a warning.
SSSOM_MAPPING_SLOTS = frozenset(
    {
        "author_id",
        "author_label",
        "comment",
        "confidence",
        "creator_id",
        "creator_label",
        "curation_rule",
        "curation_rule_text",
        "issue_tracker_item",
        "license",
        "mapping_cardinality",
        "mapping_date",
        "mapping_justification",
        "mapping_provider",
        "mapping_source",
        "mapping_tool",
        "mapping_tool_version",
        "match_string",
        "object_category",
        "object_id",
        "object_label",
        "object_match_field",
        "object_preprocessing",
        "object_source",
        "object_source_version",
        "object_type",
        "other",
        "predicate_id",
        "predicate_label",
        "predicate_modifier",
        "publication_date",
        "reviewer_id",
        "reviewer_label",
        "see_also",
        "similarity_measure",
        "similarity_score",
        "subject_category",
        "subject_id",
        "subject_label",
        "subject_match_field",
        "subject_preprocessing",
        "subject_source",
        "subject_source_version",
        "subject_type",
    }
)
# Column widths in the registry tables.
MAX_LENGTHS = {
    "set_uri": 500,
    "set_version": 100,
    "title": 500,
    "namespace": 1000,
    "canonical_iri": 1000,
    "prefix": 255,
}

# Values may legitimately be long (comments, labels); the DAG lifts this too.
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


@dataclass
class ValidationReport:
    """The outcome of checking one uploaded file."""

    data: bytes = b""
    sha256: str = ""
    issues: list[dict[str, Any]] = field(default_factory=list)
    errors: int = 0
    dropped: int = 0
    set_uri: str = ""
    set_version: str = ""
    title: str = ""
    license_id: str | None = None
    rows_checked: int = 0

    @property
    def valid(self) -> bool:
        return self.errors == 0

    @property
    def has_content_errors(self) -> bool:
        return any(
            issue["level"] == ERROR and issue["code"] not in CONFLICT_CODES
            for issue in self.issues
        )

    def add(self, level, code, message, line=None, column=None) -> None:
        if level == ERROR:
            self.errors += 1
        if len(self.issues) >= MAX_ISSUES:
            self.dropped += 1
            return
        issue: dict[str, Any] = {"level": level, "code": code, "message": message}
        if line is not None:
            issue["line"] = line
        if column is not None:
            issue["column"] = column
        self.issues.append(issue)

    def error(self, code, message, line=None, column=None) -> None:
        self.add(ERROR, code, message, line, column)

    def warning(self, code, message, line=None, column=None) -> None:
        self.add(WARNING, code, message, line, column)

    def as_dict(self) -> dict[str, Any]:
        issues = list(self.issues)
        if self.dropped:
            issues.append(
                {
                    "level": WARNING,
                    "code": "issues_truncated",
                    "message": f"{self.dropped} more issues were not listed",
                }
            )
        return {
            "valid": self.valid,
            "issues": issues,
            "set_uri": self.set_uri,
            "set_version": self.set_version,
            "title": self.title,
            "license": self.license_id,
            "rows_checked": self.rows_checked,
        }


def version_key(version: str) -> tuple[str, tuple[int, ...]] | None:
    """(scheme, sortable parts) of a valid set version, None for any other text."""
    if match := _SEMVER.fullmatch(version):
        return "semver", tuple(int(part) for part in match.groups())
    if _ISO_DATE.fullmatch(version):
        try:
            day = date.fromisoformat(version)
        except ValueError:
            return None
        return "date", (day.year, day.month, day.day)
    return None


def set_version_error(version: str, existing: list[str]) -> tuple[str, str] | None:
    """(issue code, message) if ``version`` can't follow ``existing``, else None."""
    key = version_key(version)
    if key is None:
        return None
    if version in existing:
        return (
            "set_version_exists",
            f"Version {version} already exists; publish corrections as a new "
            "mapping_set_version",
        )
    keyed = [(k, v) for v in existing if (k := version_key(v)) is not None]
    other_schemes = sorted({v for k, v in keyed if k[0] != key[0]})
    if other_schemes:
        scheme = "a SemVer version" if key[0] == "semver" else "an ISO date"
        return (
            "set_version_scheme_mismatch",
            f"Version {version} is {scheme}, but this mapping set already has "
            f"version {other_schemes[0]}; keep the same scheme",
        )
    if keyed:
        highest_key, highest = max(keyed)
        if key <= highest_key:
            return (
                "set_version_not_newer",
                f"Version {version} is not higher than the latest version "
                f"{highest}; a new version must be higher than every existing one",
            )
    return None


def is_http_iri(value: str) -> bool:
    if any(c.isspace() for c in value):
        return False
    try:
        parts = urlsplit(value)
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(parts.netloc)


class Curies:
    """Resolves a file's CURIEs against the registry's prefixes, as the DAG does."""

    def __init__(self, curie_map: dict[str, str], registered: dict[str, str]):
        self.prefixes = {**BUILTIN_PREFIXES, **curie_map}
        name_of = {namespace: name for name, namespace in registered.items()}
        self.canonical_prefix: dict[str, str] = {}
        self.conflicts: dict[str, str] = {}
        for prefix, namespace in self.prefixes.items():
            if namespace in name_of:
                self.canonical_prefix[prefix] = name_of[namespace]
            elif prefix in registered:
                self.conflicts[prefix] = (
                    f"prefix {prefix!r} is already used in the registry for "
                    f"{registered[prefix]!r}, but this file binds it to "
                    f"{namespace!r}; give that namespace another prefix name"
                )
            else:
                self.canonical_prefix[prefix] = prefix
                name_of[namespace] = prefix

    def resolve(self, value: str) -> tuple[str | None, str, str]:
        """(canonical CURIE, its prefix, ""), or (None, reason, issue code)."""
        match = CURIE.match(value)
        if not match or match["local"].startswith("//"):
            return None, f"{value!r} is not a CURIE (prefix:local_id)", "invalid_curie"
        prefix = match["prefix"]
        if prefix in self.conflicts:
            return None, f"{value!r}: {self.conflicts[prefix]}", "prefix_conflict"
        if prefix not in self.prefixes:
            return (
                None,
                f"prefix {prefix!r} of {value!r} is not in the curie_map",
                "undeclared_prefix",
            )
        canonical = self.canonical_prefix[prefix]
        return f"{canonical}:{match['local']}", canonical, ""


def find_license(iri: str) -> License | None:
    """The License an SSSOM file's license IRI refers to, if the registry has it."""
    base = iri.strip().rstrip("/").removesuffix(".html")
    rest = base.partition("://")[2]
    if not rest:
        return None
    stems = [f"{scheme}://{rest}" for scheme in ("https", "http")]
    variants = [v for s in stems for v in (s, f"{s}/", f"{s}.html")]
    ordering = ("is_deprecated", "id")
    match = License.objects.filter(license_iri__in=variants).order_by(*ordering).first()
    if match:
        return match
    see_also = reduce(or_, (Q(see_also__contains=[v]) for v in variants))
    return License.objects.filter(see_also).order_by(*ordering).first()


def _read_metadata(text: str, report: ValidationReport) -> tuple[dict | None, str, int]:
    """The parsed metadata block (None if unusable), the table text, its offset."""
    lines: list[str] = []
    pos = 0
    while pos < len(text) and text.startswith("#", pos):
        end = text.find("\n", pos)
        end = len(text) if end == -1 else end + 1
        lines.append(text[pos + 1 : end].rstrip("\r\n"))
        pos = end
        if pos > MAX_METADATA_BYTES:
            report.error(
                "metadata_too_large",
                f"The metadata block is larger than {MAX_METADATA_BYTES} bytes",
            )
            return None, "", 0
    body, count = text[pos:], len(lines)
    if not lines:
        report.error(
            "missing_metadata",
            "File has no embedded metadata block ('#'-prefixed YAML)",
            line=1,
        )
        return {}, body, count

    indents = [len(line) - len(line.lstrip(" ")) for line in lines if line.strip()]
    indent = min(indents) if indents else 0
    document = "\n".join(line[indent:] for line in lines)
    try:
        # Aliases can expand enormously in whatever later walks the metadata,
        # and SSSOM metadata has no need for them.
        for event in yaml.parse(document, Loader=yaml.SafeLoader):
            if isinstance(event, yaml.AliasEvent):
                report.error(
                    "invalid_metadata", "YAML aliases are not allowed in metadata"
                )
                return None, body, count
        loaded = yaml.safe_load(document)
    except (yaml.YAMLError, RecursionError) as e:
        mark = getattr(e, "problem_mark", None)
        report.error(
            "invalid_metadata",
            f"Metadata block is not valid YAML: {e}",
            line=(mark.line + 1) if mark else None,
        )
        return None, body, count
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        report.error(
            "invalid_metadata",
            "Metadata block must be a YAML mapping of slot: value",
            line=1,
        )
        return None, body, count
    return loaded, body, count


def _check_prefixes(
    metadata: dict[str, Any], report: ValidationReport
) -> dict[str, str] | None:
    curie_map = metadata.get("curie_map") or {}
    if not isinstance(curie_map, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in curie_map.items()
    ):
        report.error(
            "invalid_curie_map",
            "curie_map must map prefix names to namespace IRIs",
            column="curie_map",
        )
        return None
    usable = True
    for prefix, namespace in curie_map.items():
        code = message = None
        if not NCNAME.match(prefix):
            code = "invalid_curie_map"
            message = f"Prefix {prefix!r} is not a valid prefix name"
        elif prefix in BUILTIN_PREFIXES and namespace != BUILTIN_PREFIXES[prefix]:
            code = "builtin_prefix_redefined"
            message = (
                f"Built-in prefix {prefix!r} must not be redefined (as {namespace!r})"
            )
        elif prefix in RESERVED_PREFIXES and namespace != RESERVED_PREFIXES[prefix]:
            code = "prefix_conflict"
            message = (
                f"Prefix {prefix!r} is bound to {RESERVED_PREFIXES[prefix]!r} in "
                f"the registry, but to {namespace!r} in this file"
            )
        elif not is_http_iri(namespace):
            code = "invalid_namespace"
            message = (
                f"Namespace {namespace!r} of prefix {prefix!r} is not an "
                "absolute http(s) IRI"
            )
        if code:
            report.error(code, message, column="curie_map")
            usable = False
        if len(namespace) > MAX_LENGTHS["namespace"]:
            report.error(
                "value_too_long",
                f"Namespace of prefix {prefix!r} is {len(namespace)} characters; "
                f"the registry allows {MAX_LENGTHS['namespace']}",
                column="curie_map",
            )
            usable = False
    return curie_map if usable else None


def _slot_text(metadata: dict[str, Any], slot: str, report: ValidationReport) -> str:
    """A metadata slot as text; YAML reads ``1.0`` as a number."""
    value = metadata.get(slot)
    if value in (None, ""):
        return ""
    if isinstance(value, bool) or isinstance(value, (int, float)):
        report.warning(
            "coerced_value",
            f"Metadata slot {slot!r} should be a string; read {value!r} as "
            f"{str(value)!r}. Quote it in the YAML to be sure of the exact text.",
            column=slot,
        )
    return str(value)


def _check_set(metadata: dict[str, Any], report: ValidationReport) -> None:
    for slot in REQUIRED_SET_SLOTS:
        if metadata.get(slot) in (None, ""):
            report.error(
                "missing_metadata_slot",
                f"{slot} is required in the file's metadata",
                column=slot,
            )
    report.set_uri = _slot_text(metadata, "mapping_set_id", report)
    report.set_version = _slot_text(metadata, "mapping_set_version", report)
    report.title = _slot_text(metadata, "mapping_set_title", report) or report.set_uri
    if report.set_version and version_key(report.set_version) is None:
        report.error(
            "invalid_set_version",
            f"mapping_set_version {report.set_version!r} must be {VERSION_FORMAT_HINT}",
            column="mapping_set_version",
        )
    for name, value, slot in (
        ("set_uri", report.set_uri, "mapping_set_id"),
        ("set_version", report.set_version, "mapping_set_version"),
        ("title", report.title, "mapping_set_title"),
    ):
        if len(value) > MAX_LENGTHS[name]:
            report.error(
                "value_too_long",
                f"{name} is {len(value)} characters; the registry allows "
                f"{MAX_LENGTHS[name]}",
                column=slot,
            )

    license_iri = metadata.get("license")
    if license_iri not in (None, ""):
        match = find_license(str(license_iri))
        if match:
            report.license_id = match.pk
        else:
            report.warning(
                "unknown_license",
                f"License {license_iri!r} is not in the registry, so the set "
                "won't be linked to a License",
                column="license",
            )


def _extension_slots(metadata: dict[str, Any]) -> set[str]:
    definitions = metadata.get("extension_definitions")
    if not isinstance(definitions, list):
        return set()
    return {
        str(d["slot_name"])
        for d in definitions
        if isinstance(d, dict) and d.get("slot_name")
    }


def _check_header(
    header: list[str], metadata: dict[str, Any], report: ValidationReport
) -> bool:
    ok = True
    extensions = _extension_slots(metadata)
    seen: set[str] = set()
    for column in header:
        if column in seen:
            report.error(
                "duplicate_column", f"Column {column!r} appears twice", column=column
            )
            ok = False
        seen.add(column)
        if column not in SSSOM_MAPPING_SLOTS and column not in extensions:
            report.warning(
                "unknown_column",
                f"Column {column!r} is not an SSSOM slot or a declared extension; "
                "its values are kept in extra_metadata",
                column=column,
            )
    for column in REQUIRED_COLUMNS:
        if column not in seen:
            report.error(
                "missing_column",
                f"Required column {column!r} is missing",
                column=column,
            )
            ok = False
    return ok


def _check_row(line, row, curies, predicates, justifications, report) -> None:
    errors_before = report.errors
    for column in REQUIRED_COLUMNS:
        if not row[column]:
            message = f"{column} is empty"
            if column in ("subject_id", "object_id"):
                message += " (literal mappings are not supported by the registry)"
            report.error("missing_value", message, line, column)
    if report.errors > errors_before:
        return

    if row.get("confidence"):
        try:
            confidence = float(row["confidence"])
        except ValueError:
            report.error(
                "invalid_number",
                f"confidence {row['confidence']!r} is not a number",
                line,
                "confidence",
            )
        else:
            if confidence < 0 or confidence > 1:
                report.error(
                    "schema_violation",
                    f"confidence {row['confidence']} is not between 0 and 1",
                    line,
                    "confidence",
                )
    if row.get("predicate_modifier") and row["predicate_modifier"] != "Not":
        report.error(
            "schema_violation",
            f"predicate_modifier {row['predicate_modifier']!r} must be 'Not' or empty",
            line,
            "predicate_modifier",
        )

    resolved: dict[str, str] = {}
    for column in CURIE_COLUMNS:
        canonical, prefix_or_reason, code = curies.resolve(row[column])
        if canonical is None:
            report.error(code, prefix_or_reason, line, column)
            continue
        resolved[column] = canonical
        if column in ("subject_id", "object_id"):
            if len(canonical) > MAX_LENGTHS["canonical_iri"]:
                report.error(
                    "value_too_long",
                    f"{column} is {len(canonical)} characters; the registry "
                    f"allows {MAX_LENGTHS['canonical_iri']}",
                    line,
                    column,
                )
            if len(prefix_or_reason) > MAX_LENGTHS["prefix"]:
                report.error(
                    "value_too_long",
                    f"The prefix of {column} is {len(prefix_or_reason)} characters; the "
                    f"registry allows {MAX_LENGTHS['prefix']}",
                    line,
                    column,
                )
    if report.errors > errors_before:
        return

    if resolved["predicate_id"] not in predicates:
        report.error(
            "unknown_predicate",
            f"Predicate {resolved['predicate_id']!r} is not in the registry's "
            "predicate vocabulary",
            line,
            "predicate_id",
        )
    if resolved["mapping_justification"] not in justifications:
        report.error(
            "unknown_justification",
            f"Justification {resolved['mapping_justification']!r} is not in the "
            "registry's justification vocabulary",
            line,
            "mapping_justification",
        )


def _check_table(
    body: str,
    offset: int,
    metadata: dict[str, Any],
    curies: Curies,
    report: ValidationReport,
) -> None:
    predicates = set(Predicate.objects.values_list("predicate_id", flat=True))
    justifications = set(
        MappingJustification.objects.values_list("justification_id", flat=True)
    )
    reader = csv.reader(io.StringIO(body, newline=""), delimiter="\t")
    header: list[str] | None = None
    usable = True
    seen: dict[tuple, int] = {}
    start_line = offset + 1
    try:
        for values in reader:
            line = start_line
            start_line = offset + reader.line_num + 1
            if not values or values == [""]:
                continue
            if header is None:
                header = [v.strip() for v in values]
                usable = _check_header(header, metadata, report)
                if not usable:
                    return
                continue
            report.rows_checked += 1
            if len(values) != len(header):
                report.error(
                    "row_length",
                    f"Row has {len(values)} values; the header has "
                    f"{len(header)} columns",
                    line,
                )
            else:
                row = dict(zip(header, values))
                errors_before = report.errors
                _check_row(line, row, curies, predicates, justifications, report)
                if report.errors == errors_before:
                    key = (
                        curies.resolve(row["subject_id"])[0],
                        curies.resolve(row["predicate_id"])[0],
                        row.get("predicate_modifier", ""),
                        curies.resolve(row["object_id"])[0],
                        curies.resolve(row["mapping_justification"])[0],
                    )
                    if key in seen:
                        report.error(
                            "duplicate_mapping",
                            "Same subject, predicate, predicate_modifier, object "
                            f"and mapping_justification as line {seen[key]}",
                            line,
                        )
                    seen.setdefault(key, line)
            if report.rows_checked >= MAX_SAMPLE_ROWS:
                break
    except csv.Error as e:
        report.error(
            "invalid_tsv",
            f"Could not read the mappings table: {e}",
            offset + reader.line_num,
        )
        return
    if header is None:
        report.error(
            "missing_header",
            "File has no mappings table header row",
            offset + 1,
        )
    elif report.rows_checked == 0:
        report.error("no_mappings", "File contains no mappings")


def validate_upload(upload: UploadedFile) -> ValidationReport:
    """Check an uploaded file's format and content. Touches nothing."""
    report = ValidationReport()
    name = (upload.name or "").lower()
    if not name.endswith(ALLOWED_EXTENSIONS):
        report.error(
            "invalid_file_type",
            f"The file must be named *{' or *'.join(ALLOWED_EXTENSIONS)}",
        )
    limit = settings.DATA_UPLOAD_MAX_MEMORY_SIZE
    if upload.size > limit:
        report.error(
            "file_too_large",
            f"The file is {upload.size} bytes; the limit is {limit}",
        )
    if not report.valid:
        return report

    report.data = upload.read()
    report.sha256 = hashlib.sha256(report.data).hexdigest()
    try:
        text = report.data.decode("utf-8")
    except UnicodeDecodeError as e:
        report.error("invalid_encoding", f"File is not valid UTF-8: {e}")
        return report
    if text.startswith("﻿"):
        text = text[1:]
        report.warning("byte_order_mark", "File starts with a byte order mark")

    metadata, body, offset = _read_metadata(text, report)
    if metadata is None:
        return report
    curie_map = _check_prefixes(metadata, report)
    if curie_map is None:
        return report
    _check_set(metadata, report)
    registered = dict(Prefix.objects.values_list("prefix", "namespace"))
    curies = Curies(curie_map, {**registered, **RESERVED_PREFIXES})
    _check_table(body, offset, metadata, curies, report)
    return report


def in_flight_import(set_uri: str, set_version: str) -> ImportJob | None:
    """An unfinished import of this set version, from any publish route."""
    upload = Q(params__set_uri=set_uri, params__set_version=set_version)
    direct = Q(
        params__overrides__set_uri=set_uri,
        params__overrides__set_version=set_version,
    )
    return (
        ImportJob.objects.filter(
            upload | direct,
            status__in=[ImportJobStatus.PENDING, ImportJobStatus.RUNNING],
        )
        .order_by("created_at")
        .first()
    )


def _local_scan_report_exists(set_uri: str) -> bool:
    last = set_uri.rstrip("/").rsplit("/", 1)[-1]
    try:
        scan_report_uuid = uuid.UUID(last)
    except ValueError:
        return False
    return ScanReport.objects.filter(uuid=scan_report_uuid).exists()


def check_set_identity(report: ValidationReport, user) -> None:
    """Whether ``user`` may add this version to this set_uri (see the DAG's rules)."""
    set_uri, set_version = report.set_uri, report.set_version
    if not set_uri or not set_version:
        return
    if _local_scan_report_exists(set_uri):
        report.error(
            "set_uri_reserved",
            f"Mapping set {set_uri} belongs to a scan report on this Carrot "
            "instance; publish it from the scan report instead of uploading it",
            column="mapping_set_id",
        )
    first_version = (
        MappingSet.objects.filter(set_uri=set_uri).order_by("created_at", "id").first()
    )
    if first_version is not None and first_version.publisher_id != user.pk:
        report.error(
            "set_uri_not_owned",
            f"Mapping set {set_uri} already exists and was published by another "
            "user; only its publisher can add versions. Use another mapping_set_id",
            column="mapping_set_id",
        )
    existing = list(
        MappingSet.objects.filter(set_uri=set_uri).values_list("set_version", flat=True)
    )
    error = set_version_error(set_version, existing)
    if error:
        code, message = error
        report.error(
            code, f"Mapping set {set_uri}: {message}", column="mapping_set_version"
        )

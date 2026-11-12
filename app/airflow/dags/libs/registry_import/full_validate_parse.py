"""
Split an SSSOM/TSV file into its embedded metadata block and its mapping rows.

SSSOM/TSV (https://mapping-commons.github.io/sssom/spec-formats-tsv/): a YAML
metadata block on leading ``#`` lines, then a tab-separated table whose first
row is the header. Values containing tabs, line breaks or double quotes are
enclosed in double quotes, with embedded quotes doubled (RFC 4180 with tabs),
which is exactly what ``csv`` reads with a tab delimiter.

Parsing only reports problems that stop the file being read at all; checking
the content is validate.py's job.
"""

from __future__ import annotations

import csv
import io
import sys
from dataclasses import dataclass, field
from typing import Any

import yaml

ERROR = "error"
WARNING = "warning"

# Values may legitimately be long (comments, labels); lift csv's 128 KiB limit.
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


@dataclass(frozen=True)
class Issue:
    """
    One validation finding, in the shape stored in ImportJob.validation_issues
    and returned by the API's quick validation: {level, code, message, line?,
    column?}. ``line`` is the 1-based line in the file.
    """

    level: str
    code: str
    message: str
    line: int | None = None
    column: str | None = None

    def as_dict(self) -> dict[str, Any]:
        issue: dict[str, Any] = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }
        if self.line is not None:
            issue["line"] = self.line
        if self.column is not None:
            issue["column"] = self.column
        return issue


@dataclass
class ParsedSSSOM:
    metadata: dict[str, Any]
    header: list[str]
    # (line number of the row's first line, values)
    rows: list[tuple[int, list[str]]]
    issues: list[Issue] = field(default_factory=list)


def decode(data: bytes) -> tuple[str | None, list[Issue]]:
    """Decode a file as UTF-8, dropping a byte order mark (with a warning)."""
    issues: list[Issue] = []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        return None, [Issue(ERROR, "invalid_encoding", f"File is not valid UTF-8: {e}")]
    if text.startswith("﻿"):
        text = text[1:]
        issues.append(
            Issue(WARNING, "byte_order_mark", "File starts with a byte order mark")
        )
    return text, issues


def _split_metadata(text: str) -> tuple[list[str], str, int]:
    """
    The metadata lines (without '#'), the rest of the file, and the number of
    lines the metadata block takes.
    """
    meta_lines: list[str] = []
    pos = 0
    while pos < len(text) and text.startswith("#", pos):
        end = text.find("\n", pos)
        end = len(text) if end == -1 else end + 1
        meta_lines.append(text[pos + 1 : end].rstrip("\r\n"))
        pos = end
    return meta_lines, text[pos:], len(meta_lines)


def _metadata_yaml(meta_lines: list[str]) -> str:
    """
    Remove the indentation shared by every metadata line: writers may put any
    (consistent) number of spaces after '#'.
    """
    indents = [len(line) - len(line.lstrip(" ")) for line in meta_lines if line.strip()]
    indent = min(indents) if indents else 0
    return "\n".join(line[indent:] for line in meta_lines)


def parse_sssom(text: str) -> ParsedSSSOM:
    """
    Parse SSSOM/TSV text. When the file can't be read as SSSOM/TSV at all, the
    result's issues hold an error saying why, and it has no header or rows.
    """
    meta_lines, body, meta_count = _split_metadata(text)

    metadata: dict[str, Any] = {}
    issues: list[Issue] = []
    if not meta_lines:
        issues.append(
            Issue(
                ERROR,
                "missing_metadata",
                "File has no embedded metadata block ('#'-prefixed YAML)",
                line=1,
            )
        )
    else:
        try:
            loaded = yaml.safe_load(_metadata_yaml(meta_lines))
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            return ParsedSSSOM(
                {},
                [],
                [],
                [
                    Issue(
                        ERROR,
                        "invalid_metadata",
                        f"Metadata block is not valid YAML: {e}",
                        line=(mark.line + 1) if mark else None,
                    )
                ],
            )
        if loaded is None:
            loaded = {}
        if not isinstance(loaded, dict):
            return ParsedSSSOM(
                {},
                [],
                [],
                [
                    Issue(
                        ERROR,
                        "invalid_metadata",
                        "Metadata block must be a YAML mapping of slot: value",
                        line=1,
                    )
                ],
            )
        metadata = loaded

    reader = csv.reader(io.StringIO(body, newline=""), delimiter="\t")
    header: list[str] | None = None
    rows: list[tuple[int, list[str]]] = []
    try:
        start_line = meta_count + 1
        for values in reader:
            line = start_line
            start_line = meta_count + reader.line_num + 1
            if not values or values == [""]:
                continue  # blank line
            if header is None:
                header = [v.strip() for v in values]
                continue
            rows.append((line, values))
    except csv.Error as e:
        issues.append(
            Issue(
                ERROR,
                "invalid_tsv",
                f"Could not read the mappings table: {e}",
                line=meta_count + reader.line_num,
            )
        )
        return ParsedSSSOM(metadata, header or [], rows, issues)

    if header is None:
        issues.append(
            Issue(
                ERROR,
                "missing_header",
                "File has no mappings table header row",
                line=meta_count + 1,
            )
        )
        header = []
    return ParsedSSSOM(metadata, header, rows, issues)

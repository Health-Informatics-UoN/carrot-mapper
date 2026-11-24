"""
Mapping set versions: SemVer (MAJOR.MINOR.PATCH, e.g. 1.2.0) or an ISO date
(YYYY-MM-DD). Every version of a set_uri uses the same scheme, and a new
version must sort above all existing ones, so the newest version of a set is
always the highest.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date

ISO_DATE = "date"
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

SEMVER = "semver"
# NOTE: The regex below has to match the same regex used in the api/registry/versions.py file.
# Each part is capped at 9 digits so it fits the integer cast in
# api/registry/filters.py version_order(). Use with fullmatch: "$" would also
# match before a trailing newline.
_SEMVER = re.compile(r"(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})")


FORMAT_HINT = "SemVer MAJOR.MINOR.PATCH (e.g. 1.0.0) or an ISO date (YYYY-MM-DD)"


def version_key(version: str) -> tuple[str, tuple[int, ...]] | None:
    """(scheme, sortable parts) of a valid version, None for any other text."""
    if match := _SEMVER.fullmatch(version):
        return SEMVER, tuple(int(part) for part in match.groups())
    if _ISO_DATE.fullmatch(version):
        try:
            day = date.fromisoformat(version)
        except ValueError:
            return None
        return ISO_DATE, (day.year, day.month, day.day)
    return None


def set_version_error(version: str, existing: Iterable[str]) -> tuple[str, str] | None:
    """
    (issue code, message) if ``version`` can't be added after the ``existing``
    versions of its set_uri (any status), or None if it can.
    """
    key = version_key(version)
    if key is None:
        return (
            "invalid_set_version",
            f"mapping_set_version {version!r} must be {FORMAT_HINT}",
        )
    existing = list(existing)
    if version in existing:
        return (
            "set_version_exists",
            f"Version {version} already exists; publish corrections as a new "
            "mapping_set_version",
        )
    keyed = [(k, v) for v in existing if (k := version_key(v)) is not None]
    other_schemes = sorted({v for k, v in keyed if k[0] != key[0]})
    if other_schemes:
        return (
            "set_version_scheme_mismatch",
            f"Version {version} is {_scheme_name(key[0])}, but this mapping set "
            f"already has version {other_schemes[0]}; keep the same scheme",
        )
    if keyed:
        highest_key, highest = max(keyed)
        if key <= highest_key:
            return (
                "set_version_not_newer",
                f"Version {version} is not higher than the latest version {highest}; "
                "a new version must be higher than every existing one",
            )
    return None


def _scheme_name(scheme: str) -> str:
    return "a SemVer version" if scheme == SEMVER else "an ISO date"

"""
SemVer versions of mapping sets published from a scan report.

The registry accepts SemVer (MAJOR.MINOR.PATCH) or ISO date versions, and a
new version must be higher than every existing one of its set_uri (enforced
by the registry_import DAG, airflow libs/registry_import/set_versions.py).
A direct publish always uses SemVer: the user picks the kind of release and
the next version is derived from the highest existing one.
"""

import re
from collections.abc import Iterable

from django.db import models

FIRST_VERSION = "1.0.0"

_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class ReleaseType(models.TextChoices):
    MAJOR = "major", "Major"
    MINOR = "minor", "Minor"
    PATCH = "patch", "Patch"


class NotSemVer(ValueError):
    """An existing version of the set isn't SemVer, so it can't be bumped."""


def parse_semver(version: str) -> tuple[int, int, int] | None:
    match = _SEMVER.match(version)
    if match is None:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def latest_semver(versions: Iterable[str]) -> str | None:
    """The highest of ``versions``; raises NotSemVer if any isn't SemVer."""
    parsed = []
    for version in versions:
        parts = parse_semver(version)
        if parts is None:
            raise NotSemVer(version)
        parsed.append((parts, version))
    return max(parsed)[1] if parsed else None


def bump(latest: str | None, release_type: str) -> str:
    """The version after ``latest`` for a release of ``release_type``."""
    if latest is None:
        return FIRST_VERSION
    major, minor, patch = parse_semver(latest)
    if release_type == ReleaseType.MAJOR:
        return f"{major + 1}.0.0"
    if release_type == ReleaseType.MINOR:
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"

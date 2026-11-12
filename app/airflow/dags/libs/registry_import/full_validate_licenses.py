"""
full_validate helper: link a mapping set's license IRI to a registry_license row.

Read-only: registry_license is filled by the license_sync DAG (SPDX License
List); this module never adds licenses.

A Mapper direct publish (and any request that sends a License id) writes the
row's own license_iri into the file, which matches exactly. An uploaded SSSOM
file names its license however its author chose, usually the
creativecommons.org URL rather than the SPDX one, so matching also tries each
row's see_also IRIs, ignoring http/https, trailing slashes, /legalcode,
/deed.xx and .html.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

_LICENSE_IRI_SUFFIX = re.compile(r"(/(legalcode|deed)(\.[a-z_-]+)?|\.(html|txt|json))$")


def normalise_license_iri(iri: str) -> str:
    """A comparison key for a license IRI (not for storing)."""
    key = iri.strip().lower()
    if key.startswith("http://"):
        key = "https://" + key[len("http://") :]
    key = key.rstrip("/")
    key = _LICENSE_IRI_SUFFIX.sub("", key)
    return key.rstrip("/")


@dataclass(frozen=True)
class License:
    """A registry_license row."""

    id: str
    license_iri: str
    see_also: tuple[str, ...] = ()
    is_deprecated: bool = False


class LicenseLookup:
    """Finds the registry_license row an IRI names, by license_iri or see_also."""

    def __init__(self, licenses: Iterable[License]):
        self._by_iri: dict[str, License] = {}
        licenses = list(licenses)
        for license in licenses:
            for iri in license.see_also:
                self._by_iri.setdefault(normalise_license_iri(iri), license)
        # a license's own IRI wins over another's see_also
        for license in licenses:
            self._by_iri[normalise_license_iri(license.license_iri)] = license

    def find(self, iri: str | None) -> License | None:
        if not iri:
            return None
        return self._by_iri.get(normalise_license_iri(str(iri)))

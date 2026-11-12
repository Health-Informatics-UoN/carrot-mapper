"""
Turn the SPDX License List (https://spdx.org/licenses/licenses.json) into rows
for the Mappings Registry license table (registry_license).
"""

from typing import Any, TypedDict

SPDX_LICENSE_IRI = "https://spdx.org/licenses/"


class LicenseRow(TypedDict):
    id: str
    license_iri: str
    spdx_id: str
    label: str
    is_open: bool
    is_deprecated: bool
    see_also: list[str]


def parse_spdx_licenses(payload: dict[str, Any]) -> list[LicenseRow]:
    """
    One row per SPDX license, keyed by its SPDX license ID.

    Raises ValueError if the payload isn't a license list, so a bad response
    fails the run instead of syncing nothing.
    """
    licenses = payload.get("licenses") if isinstance(payload, dict) else None
    if not licenses:
        raise ValueError("SPDX response has no licenses")

    rows: list[LicenseRow] = []
    for lic in licenses:
        spdx_id = lic["licenseId"]
        rows.append(
            {
                "id": spdx_id,
                "license_iri": f"{SPDX_LICENSE_IRI}{spdx_id}",
                "spdx_id": spdx_id,
                "label": lic["name"],
                # SPDX flags are null when a license was never reviewed.
                "is_open": bool(lic.get("isOsiApproved") or lic.get("isFsfLibre")),
                "is_deprecated": bool(lic.get("isDeprecatedLicenseId")),
                "see_also": list(lic.get("seeAlso") or []),
            }
        )
    return rows

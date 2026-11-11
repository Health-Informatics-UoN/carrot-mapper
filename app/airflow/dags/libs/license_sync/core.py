import json
import logging

import requests
from libs.db import pg_hook
from libs.license_sync.spdx import LicenseRow, parse_spdx_licenses
from libs.settings import SPDX_LICENSE_LIST_URL

# `version` is left alone on update: SPDX has no separate version field.
# Licenses are never deleted, as mapping sets may still reference them.
upsert_license_query = """
    INSERT INTO registry_license
        (id, license_iri, spdx_id, label, version, is_open, is_deprecated, see_also)
    VALUES
        (%(id)s, %(license_iri)s, %(spdx_id)s, %(label)s, '', %(is_open)s,
         %(is_deprecated)s, %(see_also)s::jsonb)
    ON CONFLICT (id) DO UPDATE SET
        license_iri = EXCLUDED.license_iri,
        spdx_id = EXCLUDED.spdx_id,
        label = EXCLUDED.label,
        is_open = EXCLUDED.is_open,
        is_deprecated = EXCLUDED.is_deprecated,
        see_also = EXCLUDED.see_also;
"""


def fetch_spdx_license_list() -> dict:
    response = requests.get(SPDX_LICENSE_LIST_URL, timeout=60)
    response.raise_for_status()
    return response.json()


def upsert_licenses(rows: list[LicenseRow]) -> None:
    """Upsert every row in one transaction, so a failed run changes nothing."""
    params = [{**row, "see_also": json.dumps(row["see_also"])} for row in rows]
    with pg_hook.get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(upsert_license_query, params)
        conn.commit()


def sync_spdx_licenses(**kwargs) -> None:
    payload = fetch_spdx_license_list()
    rows = parse_spdx_licenses(payload)
    upsert_licenses(rows)
    logging.info(
        "Synced %d licenses from SPDX License List %s",
        len(rows),
        payload.get("licenseListVersion", "unknown"),
    )

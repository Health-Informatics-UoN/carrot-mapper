"use server";

import request from "@/lib/api/request";

export interface RegistryLicense {
  id: string;
  spdx_id?: string;
  label: string;
  is_open: boolean;
  is_deprecated?: boolean;
}

type LicensesResponse =
  | RegistryLicense[]
  | {
      results: RegistryLicense[];
      next: string | null;
    };

export type RegistryLicensesResult =
  | { ok: true; licenses: RegistryLicense[] }
  | { ok: false; message: string; licenses: [] };

/**
 * Fetch licences from the Carrot backend, never directly from spdx.org.
 * Requires the planned GET /api/licenses/ endpoint. The uploaded backend
 * snapshot has a License model but no route yet.
 */
export async function getRegistryLicenses(): Promise<RegistryLicensesResult> {
  try {
    const licenses: RegistryLicense[] = [];
    let path = "licenses/?page_size=1000";
    // Accommodate ordinary DRF pagination and unpaginated list responses.
    for (let page = 0; page < 30; page++) {
      const data = await request<LicensesResponse>(path, {
        cache: "no-store",
      });
      if (Array.isArray(data)) {
        licenses.push(...data);
        break;
      }
      licenses.push(...data.results);
      if (!data.next) break;
      // request() always prefixes the API base URL; send only a relative path.
      const next = new URL(data.next, "http://localhost");
      path = `licenses/${next.search}`;
      if (page === 29) throw new Error("License pagination limit reached");
    }
    return { ok: true, licenses };
  } catch {
    return {
      ok: false,
      licenses: [],
      message: "Could not load licences from the Carrot API. Check GET /licenses/.",
    };
  }
}

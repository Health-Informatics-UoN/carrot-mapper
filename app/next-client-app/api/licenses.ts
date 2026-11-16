"use server";

import request from "@/lib/api/request";

export interface RegistryLicense {
  id: string;
  license_iri: string;
  label: string;
  is_open: boolean;
  is_deprecated: boolean;
}

export type RegistryLicensesResult =
  | { ok: true; licenses: RegistryLicense[] }
  | { ok: false; message: string; licenses: [] };

export async function getRegistryLicenses(): Promise<RegistryLicensesResult> {
  try {
    const licenses = await request<RegistryLicense[]>("v2/registry/licenses/", {
      next: { revalidate: 86_400 },
    });
    return { ok: true, licenses };
  } catch {
    return {
      ok: false,
      licenses: [],
      message: "Could not load licences from the Carrot API.",
    };
  }
}

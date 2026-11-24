"use server";

import request from "@/lib/api/request";
import { ApiError } from "@/lib/api/error";

/* ---- Interfaces ---- */

export type ReleaseType = "major" | "minor" | "patch";

export interface PublishToRegistryPayload {
  title: string;
  description: string;
  release_type: ReleaseType;
  include_author_orcid_ids: boolean;
  license: string;
}

interface RegistryPublishResponse {
  import_job_id: string;
  status: string;
  set_version: string;
}

export interface RegistryPublishVersions {
  latest_version: string | null;
  next_versions: Record<ReleaseType, string>;
}

/* ---- API Functions ---- */

const publishUrl = (scanReportId: string) =>
  `v2/registry/scanreports/${encodeURIComponent(scanReportId)}/registry-publish/`;

export async function getRegistryPublishVersions(
  scanReportId: string,
): Promise<{ ok: true; versions: RegistryPublishVersions } | { ok: false; message: string }> {
  try {
    const versions = await request<RegistryPublishVersions>(publishUrl(scanReportId), {
      cache: "no-store",
    });
    return { ok: true, versions };
  } catch (error) {
    if (error instanceof ApiError && error.message !== "An error occurred") {
      return { ok: false, message: error.message };
    }
    return { ok: false, message: "Could not load the mapping set's versions." };
  }
}

export async function publishScanReportToRegistry(
  scanReportId: string,
  payload: PublishToRegistryPayload,
): Promise<{ ok: true; job: RegistryPublishResponse } | { ok: false; message: string }> {
  try {
    const job = await request<RegistryPublishResponse>(publishUrl(scanReportId), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return { ok: true, job };
  } catch (error) {
    if (error instanceof ApiError && error.message !== "An error occurred") {
      return { ok: false, message: error.message };
    }
    return { ok: false, message: "Could not start publication. Please try again." };
  }
}

"use server";

import request from "@/lib/api/request";
import { ApiError } from "@/lib/api/error";

export interface PublishToRegistryPayload {
  title: string;
  description: string;
  set_version: string;
  include_author_orcid_ids: boolean;
  license: string;
}

interface RegistryPublishResponse {
  import_job_id: string;
  status: string;
}

export async function publishScanReportToRegistry(
  scanReportId: string,
  payload: PublishToRegistryPayload,
): Promise<{ ok: true; job: RegistryPublishResponse } | { ok: false; message: string }> {
  try {
    const job = await request<RegistryPublishResponse>(
      `v2/registry/scanreports/${encodeURIComponent(scanReportId)}/registry-publish/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    return { ok: true, job };
  } catch (error) {
    if (error instanceof ApiError && error.message !== "An error occurred") {
      return { ok: false, message: error.message };
    }
    return { ok: false, message: "Could not start publication. Please try again." };
  }
}
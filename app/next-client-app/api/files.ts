"use server";

import request from "@/lib/api/request";
import { revalidatePath } from "next/cache";

const fetchKeys = {
  list: (scan_report_id: number, filter?: string) =>
    `v2/scanreports/${scan_report_id}/rules/downloads/?${filter}`,
  requestFile: (scan_report_id: number) =>
    `v2/scanreports/${scan_report_id}/rules/downloads/`,
  downloadFile: (scan_report_id: number, file_id: number) =>
    `v2/scanreports/${scan_report_id}/rules/downloads/${file_id}/`,
};

export async function list(
  scan_report_id: number,
  filter: string | undefined
): Promise<PaginatedResponse<FileDownload> | null> {
  try {
    return await request<PaginatedResponse<FileDownload>>(
      fetchKeys.list(scan_report_id, filter)
    );
  } catch (error) {
    return null;
  }
}

export async function requestFile(
  scan_report_id: number,
  file_type: FileTypeFormat
): Promise<{ success: boolean; errorMessage?: string }> {
  try {
    await request(fetchKeys.requestFile(scan_report_id), {
      method: "POST",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify({
        scan_report_id: scan_report_id,
        file_type: file_type,
      }),
    });
    revalidatePath(`/scanreports/${scan_report_id}/downloads`);
    return { success: true };
  } catch (error: any) {
    return { success: false, errorMessage: error.message };
  }
}

export async function downloadFile(
  scan_report_id: number,
  file_id: number,
  file_type: string
): Promise<{ success: boolean; errorMessage?: string; data?: any }> {
  try {
    const response = await request(
      fetchKeys.downloadFile(scan_report_id, file_id)
    );
    if (file_type == "mapping_json") {
      return { success: true, data: JSON.parse(response) };
    }
    if (file_type == "mapping_csv") {
      return { success: true, data: response };
    }
    return { success: false, errorMessage: "Unsupported file type" };
  } catch (error: any) {
    return { success: false, errorMessage: error.message };
  }
}

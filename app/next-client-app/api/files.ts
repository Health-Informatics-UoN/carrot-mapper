"use server";

import request from "@/lib/api/request";
import { revalidatePath } from "next/cache";

const fetchKeys = {
  list: (scan_report_id: number, filter?: string) =>
    `v2/scanreports/${scan_report_id}/rules/downloads/?${filter}`,
  requestFile: (scan_report_id: number) =>
    `v2/scanreports/${scan_report_id}/rules/downloads/`,
  downloadFile: (scan_report_id: number, file_id?: number) =>
    file_id
      ? `v2/scanreports/${scan_report_id}/rules/downloads/${file_id}/`
      : `v2/scanreports/${scan_report_id}/download/`,
  deleteFile: (scan_report_id: number, file_id: number) =>
    `v2/scanreports/${scan_report_id}/rules/delete/${file_id}/`,
};

export async function list(
  scan_report_id: number,
  filter: string | undefined,
): Promise<PaginatedResponse<FileDownload> | null> {
  try {
    return await request<PaginatedResponse<FileDownload>>(
      fetchKeys.list(scan_report_id, filter),
    );
  } catch (error) {
    return null;
  }
}

export async function requestFile(
  scan_report_id: number,
  file_type: FileTypeFormat,
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
  file_id?: number,
): Promise<{
  success: boolean;
  errorMessage?: string;
  data?: any;
  blob?: Blob;
  downloadUrl?: string;
}> {
  try {
    if (!file_id) {
      // The case of SR exporting - keep existing logic for now
      const response = await request(fetchKeys.downloadFile(scan_report_id), {
        download: true,
      });
      // Convert Blob to Base64 string to be able to pass to the client
      const arrayBuffer = await response.arrayBuffer();
      const base64String = Buffer.from(arrayBuffer).toString("base64");

      return { success: true, data: base64String };
    } else {
      // The case of mapping rules file downloading - use streaming API route
      const downloadUrl = `/api/download/${scan_report_id}/${file_id}`;
      return { success: true, downloadUrl };
    }
  } catch (error: any) {
    return { success: false, errorMessage: error.message };
  }
}

export async function deleteFile(
  scan_report_id: number,
  file_id: number,
): Promise<{ success: boolean; errorMessage?: string }> {
  try {
    await request(fetchKeys.deleteFile(scan_report_id, file_id), {
      method: "DELETE",
    });
    revalidatePath(`/scanreports/${scan_report_id}/downloads`);
    return { success: true };
  } catch (error: any) {
    return { success: false, errorMessage: error.message };
  }
}

"use server";
import request from "@/lib/api/request";

const fetchKeys = {
  scanReportLogs: (scanReportId: string | number, filter?: string) =>
    `v2/scanreports/${scanReportId}/logs/?${filter}`,
  datasetLogs: (datasetId: string | number, filter?: string) =>
    `v2/datasets/${datasetId}/logs/?${filter}`,
};

export async function getScanReportActivityLogs(
  scanReportId: string | number,
  filter: string | undefined,
): Promise<PaginatedResponse<ActivityLog> | null> {
  try {
    return await request<PaginatedResponse<ActivityLog>>(
      fetchKeys.scanReportLogs(scanReportId, filter),
    );
  } catch (error) {
    console.warn("Failed to fetch scan report activity logs.");
    return null;
  }
}

export async function getDatasetActivityLogs(
  datasetId: string | number,
  filter: string | undefined,
): Promise<PaginatedResponse<ActivityLog> | null> {
  try {
    return await request<PaginatedResponse<ActivityLog>>(
      fetchKeys.datasetLogs(datasetId, filter),
    );
  } catch (error) {
    console.warn("Failed to fetch dataset activity logs.");
    return null;
  }
}

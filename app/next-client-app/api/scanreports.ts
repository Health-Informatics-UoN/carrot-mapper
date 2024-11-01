"use server";
import { revalidatePath } from "next/cache";
import request from "@/lib/api/request";
import { redirect } from "next/navigation";
import { fetchAllPages } from "@/lib/api/utils";

const fetchKeys = {
  index: (filter?: string) =>
    filter ? `v2/scanreports/?${filter}` : "v2/scanreports/",
  get: (id: string | number) => `v2/scanreports/${id}/`,
  permissions: (id: string) => `v2/scanreports/${id}/permissions/`,
  table: (scanReportId: string | number, tableId: string | number) =>
    `v2/scanreports/${scanReportId}/tables/${tableId}/`,
  tables: (scanReportId: string, filter?: string) =>
    `v2/scanreports/${scanReportId}/tables/?${filter}`,
  field: (
    scanReportId: string | number,
    tableId: string | number,
    fieldId: string | number | undefined
  ) => `v2/scanreports/${scanReportId}/tables/${tableId}/fields/${fieldId}/`,
  fields: (scanReportId: string, tableId: string, filter?: string) =>
    `v2/scanreports/${scanReportId}/tables/${tableId}/fields/?${filter}`,
  values: (
    scanReportId: string,
    tableId: string,
    fieldId: string,
    filter?: string
  ) =>
    `v2/scanreports/${scanReportId}/tables/${tableId}/fields/${fieldId}/values/?${filter}`,
};

export async function getScanReports(
  filter: string | undefined
): Promise<PaginatedResponse<ScanReport>> {
  try {
    return await request<PaginatedResponse<ScanReport>>(
      fetchKeys.index(filter)
    );
  } catch (error) {
    console.warn("Failed to fetch data.");
    return { count: 0, next: null, previous: null, results: [] };
  }
}

export async function createScanReport(data: FormData) {
  try {
    await request(fetchKeys.index(), {
      method: "POST",
      body: data,
    });
  } catch (error: any) {
    // Only return a response when there is an error
    return { errorMessage: error.message };
  }
  redirect(`/scanreports/`);
}

export async function getScanReport(id: string): Promise<ScanReport | null> {
  try {
    return await request<ScanReport>(fetchKeys.get(id));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return null;
  }
}

export async function updateScanReport(
  id: number,
  data: {},
  needRedirect?: boolean
) {
  try {
    await request(fetchKeys.get(id), {
      method: "PATCH",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify(data),
    });
    revalidatePath("/scanreports/");
  } catch (error: any) {
    // Only return a response when there is an error
    return { errorMessage: error.message };
  }
  if (needRedirect) {
    redirect(`/scanreports/`);
  }
}

export async function deleteScanReport(id: number) {
  try {
    await request(fetchKeys.get(id), {
      method: "DELETE",
      headers: {
        "Content-type": "application/json",
      },
    });
    revalidatePath("/scanreports/");
  } catch (error: any) {
    return { errorMessage: error.message };
  }
}

/**
 * Get the current users permissions for a Scan Report.
 * @param id The Id of the Scan Report
 * @returns A object with a list of the users permissions.
 */
export async function getScanReportPermissions(
  id: string
): Promise<PermissionsResponse> {
  try {
    return await request<PermissionsResponse>(fetchKeys.permissions(id));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return { permissions: [] };
  }
}

export async function getScanReportTable(
  scanReportId: string,
  tableId: string
): Promise<ScanReportTable> {
  try {
    return await request<ScanReportTable>(
      fetchKeys.table(scanReportId, tableId)
    );
  } catch (error) {
    console.warn("Failed to fetch data.");
    return {
      id: 0,
      name: "",
      scan_report: 0,
      person_id: null,
      created_at: new Date(),
      updated_at: new Date(),
      date_event: null,
      permissions: [],
      death_table: false,
    };
  }
}

export async function updateScanReportTable(
  scanReportId: string | number,
  tableId: string | number,
  data: {}
) {
  try {
    await request(fetchKeys.table(scanReportId, tableId), {
      method: "PATCH",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify(data),
    });
  } catch (error: any) {
    return { errorMessage: error.message };
  }
  // TODO: remove redirect here.
  redirect(`/scanreports/${scanReportId}/`);
}

export async function getScanReportTables(
  scanReportId: string,
  filter: string | undefined
): Promise<PaginatedResponse<ScanReportTable>> {
  try {
    return await request<PaginatedResponse<ScanReportTable>>(
      fetchKeys.tables(scanReportId, filter)
    );
  } catch (error) {
    console.warn("Failed to fetch data.");
    return { count: 0, next: null, previous: null, results: [] };
  }
}

export async function getScanReportFields(
  scanReportId: string,
  tableId: string,
  filter: string | undefined
): Promise<PaginatedResponse<ScanReportField>> {
  try {
    return await request<PaginatedResponse<ScanReportField>>(
      fetchKeys.fields(scanReportId, tableId, filter)
    );
  } catch (error) {
    console.warn("Failed to fetch data.");
    return { count: 0, next: null, previous: null, results: [] };
  }
}

export async function getScanReportField(
  scanReportId: string,
  tableId: string,
  fieldId: string | number | undefined
): Promise<ScanReportField> {
  try {
    return await request<ScanReportField>(
      fetchKeys.field(scanReportId, tableId, fieldId)
    );
  } catch (error) {
    console.warn("Failed to fetch data. Passed ID could be null");
    return {
      id: 0,
      created_at: new Date(),
      updated_at: new Date(),
      name: "",
      description_column: "",
      type_column: "",
      max_length: 0,
      nrows: 0,
      nrows_checked: 0,
      fraction_empty: "",
      nunique_values: 0,
      fraction_unique: "",
      ignore_column: null,
      is_patient_id: false,
      is_ignore: false,
      classification_system: null,
      pass_from_source: false,
      concept_id: 0,
      permissions: [],
      field_description: null,
      scan_report_table: 0,
    };
  }
}

export async function updateScanReportField(
  scanReportId: string | number,
  tableId: string | number,
  fieldId: string,
  data: {}
) {
  try {
    await request(fetchKeys.field(scanReportId, tableId, fieldId), {
      method: "PATCH",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify(data),
    });
  } catch (error: any) {
    return { errorMessage: error.message };
  }
}

export async function getAllScanReportFields(
  scanReportId: string,
  tableId: string,
  filter: string | undefined
): Promise<ScanReportField[]> {
  try {
    return await fetchAllPages<ScanReportField>(
      fetchKeys.fields(scanReportId, tableId, filter)
    );
  } catch (error) {
    console.warn("Failed to fetch data.");
    return [];
  }
}

export async function getScanReportValues(
  scanReportId: string,
  tableId: string,
  fieldId: string,
  filter: string | undefined
): Promise<PaginatedResponse<ScanReportValue>> {
  try {
    return await request<PaginatedResponse<ScanReportValue>>(
      fetchKeys.values(scanReportId, tableId, fieldId, filter)
    );
  } catch (error) {
    console.warn("Failed to fetch data.");
    return { count: 0, next: null, previous: null, results: [] };
  }
}

"use server";
import request from "@/lib/api/request";
import { fetchAllPages } from "@/lib/api/utils";
import { revalidatePath } from "next/cache";

const fetchKeys = {
  conceptFilter: (filter: string) =>
    `v2/omop/conceptsfilter/?concept_id__in=${filter}`,
  addConcept: "v2/scanreports/concepts/",
  deleteConcept: (conceptId: number) => `v2/scanreports/concepts/${conceptId}/`,
  scanreportConcepts: (filter?: string) => `v2/scanreports/concepts/?${filter}`,
  scanreportConceptDetail: (scanReportId: string, tableId: string, fieldId: string, valueId: string, conceptId: string) => `v3/scanreports/${scanReportId}/tables/${tableId}/fields/${fieldId}/values/${valueId}/concepts/${conceptId}/`,
};

export async function getAllScanReportConcepts(
  filter: string | undefined,
): Promise<ScanReportConcept[]> {
  try {
    return await fetchAllPages<ScanReportConcept>(
      fetchKeys.scanreportConcepts(filter),
    );
  } catch (error) {
    console.warn("Failed to fetch data.");
    return [];
  }
}

export async function getAllConceptsFiltered(
  filter: string,
): Promise<Concept[]> {
  try {
    return await fetchAllPages<Concept>(fetchKeys.conceptFilter(filter));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return [];
  }
}

export async function addConcept(data: {}) {
  try {
    await request(fetchKeys.addConcept, {
      method: "POST",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify(data),
    });
  } catch (error: any) {
    // Only return a response when there is an error
    return { errorMessage: error.message };
  }
}

export async function addConceptV3(data: {}, path: string) {
  try {
    await request(fetchKeys.addConcept, {
      method: "POST",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify(data),
    });
    revalidatePath(path);
  } catch (error: any) {
    // Only return a response when there is an error
    return { errorMessage: error.message };
  }
}

export async function deleteConcept(conceptId: number) {
  await request(fetchKeys.deleteConcept(conceptId), {
    method: "DELETE",
    headers: {
      "Content-type": "application/json",
    },
  });
}

export async function deleteConceptV3(conceptId: number, path: string) {
  await request(fetchKeys.deleteConcept(conceptId), {
    method: "DELETE",
    headers: {
      "Content-type": "application/json",
    },
  });
  revalidatePath(path);
}

export async function getScanReportConceptDetail(
  scanReportId: string,
  tableId: string,
  fieldId: string,
  valueId: string,
  conceptId: string,
): Promise<ScanReportConceptDetailV3> {
  return await request(fetchKeys.scanreportConceptDetail(scanReportId, tableId, fieldId, valueId, conceptId));
}

export async function updateScanReportConceptDetail(
  scanReportId: string,
  tableId: string,
  fieldId: string,
  valueId: string,
  conceptId: string,
  data: {},
): Promise<ScanReportConceptDetailV3> {
  return await request(fetchKeys.scanreportConceptDetail(scanReportId, tableId, fieldId, valueId, conceptId), {
    method: "PATCH",
    headers: {
      "Content-type": "application/json",
    },
    body: JSON.stringify(data),
  });
}

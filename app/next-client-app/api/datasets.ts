"use server";
import { revalidatePath } from "next/cache";
import request from "@/lib/api/request";
import { redirect } from "next/navigation";

const fetchKeys = {
  list: (filter?: string) =>
    filter
      ? `v2/datasets/datasets_data_partners/?${filter}`
      : "v2/datasets/datasets_data_partners/",
  dataset: (id: string) => `v2/datasets/${id}/`,
  datasetList: (dataPartnerId?: string) =>
    dataPartnerId
      ? `v2/datasets/?data_partner=${dataPartnerId}&hidden=false`
      : "v2/datasets/",
  dataPartners: () => "v2/datapartners/",
  users: () => "v2/usersfilter/?is_active=true",
  updateDataset: (id: number) => `v2/datasets/${id}/`,
  permissions: (id: string) => `v2/datasets/${id}/permissions/`,
  create: "v2/datasets/",
};

export async function getDataSets(
  filter: string | undefined
): Promise<PaginatedResponse<DataSet>> {
  try {
    return await request<DataSet>(fetchKeys.list(filter));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return { count: 0, next: null, previous: null, results: [] };
  }
}

export async function getDataSet(id: string): Promise<DataSetSRList> {
  try {
    return await request<DataSetSRList>(fetchKeys.dataset(id));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return {
      id: 0,
      created_at: new Date(),
      updated_at: new Date(),
      name: "",
      visibility: "",
      hidden: null,
      data_partner: {
        id: 0,
        name: "",
        created_at: new Date(),
        updated_at: new Date(),
      },
      viewers: [],
      admins: [],
      editors: [],
      projects: [],
    };
  }
}

export async function getDatasetList(
  filter?: string
): Promise<DataSetSRList[]> {
  try {
    return await request<DataSetSRList>(fetchKeys.datasetList(filter));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return [];
  }
}

export async function getDataPartners(): Promise<DataPartner[]> {
  try {
    return request<DataPartner[]>(fetchKeys.dataPartners());
  } catch (error) {
    console.warn("Failed to fetch data.");
    return [];
  }
}

export async function getDataUsers(): Promise<User[]> {
  try {
    return request<User[]>(fetchKeys.users());
  } catch (error) {
    console.warn("Failed to fetch data.");
    return [];
  }
}

export async function archiveDataSets(id: number, hidden: boolean) {
  try {
    await request(fetchKeys.updateDataset(id), {
      method: "PATCH",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify({ hidden: hidden }),
    });
    revalidatePath("/datasets/");
  } catch (error: any) {
    // Only return a response when there is an error
    return { errorMessage: error.message };
  }
}

export async function updateDatasetDetails(id: number, data: {}) {
  try {
    await request(fetchKeys.updateDataset(id), {
      method: "PATCH",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify(data),
    });
  } catch (error: any) {
    return { errorMessage: error.message };
  }
  redirect(`/datasets/${id}/`);
}

export async function getDatasetPermissions(
  id: string
): Promise<PermissionsResponse> {
  try {
    return await request<PermissionsResponse>(fetchKeys.permissions(id));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return { permissions: [] };
  }
}

export async function createDataset(data: {}) {
  try {
    await request(fetchKeys.create, {
      method: "POST",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify(data),
    });
    revalidatePath("");
  } catch (error: any) {
    return { errorMessage: error.message };
  }
}

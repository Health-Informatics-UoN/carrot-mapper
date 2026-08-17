"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import request from "@/lib/api/request";
import { fetchAllPages } from "@/lib/api/utils";

const fetchKeys = {
  list: (filter?: string) => (filter ? `projects/?${filter}` : "projects/"),
  projectsDataset: (dataset: string) => `projects/?dataset=${dataset}`,
  project: (id: string) => `projects/${id}/`,
  permissions: (id: string) => `projects/${id}/permissions/`,
  create: "projects/",
};

export async function getProjectsList(
  filter?: string | undefined
): Promise<PaginatedResponse<Project>> {
  try {
    return await request<Project>(fetchKeys.list(filter));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return { count: 0, next: null, previous: null, results: [] };
  }
}

export async function getAllProjects(): Promise<Project[]> {
  try {
    // Add a fake filter to the query to ensure the fetchAllPages call works normally
    return await fetchAllPages<Project>(fetchKeys.list(" "));
  } catch (error) {
    console.warn("Failed to fetch all projects data");
    return [];
  }
}

export async function getProjectsDataset(
  dataset: string
): Promise<PaginatedResponse<Project>> {
  try {
    return request<Project>(fetchKeys.projectsDataset(dataset));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return { count: 0, next: null, previous: null, results: [] };
  }
}

export async function getProject(id: string): Promise<Project | null> {
  try {
    return await request<Project | null>(fetchKeys.project(id));
  } catch (error) {
    return null;
  }
}

export async function getProjectPermissions(
  id: string
): Promise<PermissionsResponse> {
  try {
    return await request<PermissionsResponse>(fetchKeys.permissions(id));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return { permissions: [] };
  }
}

export async function createProject(data: {}) {
  try {
    await request(fetchKeys.create, {
      method: "POST",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify(data),
    });
    revalidatePath("/projects/");
  } catch (error: any) {
    return { errorMessage: error.message };
  }
}

export async function updateProjectDetails(id: number, data: {}) {
  try {
    await request(fetchKeys.project(String(id)), {
      method: "PATCH",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify(data),
    });
  } catch (error: any) {
    return { errorMessage: error.message };
  }
  redirect(`/projects/${id}/`);
}

"use server";

import request from "@/lib/api/request";

const fetchKeys = {
  list: (filter?: string) => (filter ? `projects/?${filter}` : "projects/"),
  projects: "projects/",
  projectsDataset: (dataset: string) => `projects/?dataset=${dataset}`,
  project: (id: string) => `projects/${id}/`,
};

export async function getProjectsList(
  filter: string | undefined
): Promise<PaginatedResponse<Project>> {
  try {
    return await request<Project>(fetchKeys.list(filter));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return { count: 0, next: null, previous: null, results: [] };
  }
}

export async function getProjectsDataset(dataset: string): Promise<Project[]> {
  try {
    return request<Project[]>(fetchKeys.projectsDataset(dataset));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return [];
  }
}

export async function getProjects(): Promise<Project[]> {
  try {
    return request<Project[]>(fetchKeys.projects);
  } catch (error) {
    console.warn("Failed to fetch data.");
    return [];
  }
}

export async function getproject(id: string): Promise<Project> {
  try {
    return await request<Project>(fetchKeys.project(id));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return {
      id: 0,
      created_at: new Date(),
      updated_at: new Date(),
      name: "",
      datasets: [],
      members: [],
    };
  }
}

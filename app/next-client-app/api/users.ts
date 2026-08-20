"use server";
import { revalidatePath } from "next/cache";
import request from "@/lib/api/request";

const fetchKeys = {
  currentUser: () => `user/me/`,
  profile: (id: string) => `v2/users/${id}/`,
  sharedProjects: (id: string) => `v2/users/${id}/shared-projects/`,
};

export async function getCurrentUser(): Promise<User | null> {
  try {
    return await request<User>(fetchKeys.currentUser());
  } catch (error) {
    return null;
  }
}

export async function getUserProfile(id: string): Promise<UserProfile | null> {
  try {
    return await request<UserProfile>(fetchKeys.profile(id));
  } catch (error) {
    return null;
  }
}

export async function getSharedProjects(id: string): Promise<ProjectName[]> {
  try {
    return await request<ProjectName[]>(fetchKeys.sharedProjects(id));
  } catch (error) {
    console.warn("Failed to fetch shared projects.");
    return [];
  }
}

export async function updateUserProfile(id: number, data: {}) {
  try {
    await request(fetchKeys.profile(String(id)), {
      method: "PATCH",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify(data),
    });
  } catch (error: any) {
    return { errorMessage: error.message };
  }
  revalidatePath(`/users/${id}/`);
}

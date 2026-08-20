"use server";

import request from "@/lib/api/request";

const fetchKeys = {
  list: (filter?: string) =>
    filter ? `v2/omop/vocabularies/?${filter}` : "v2/omop/vocabularies/",
};

export async function getVocabulariesList(
  filter?: string | undefined
): Promise<PaginatedResponse<Vocabulary>> {
  try {
    return await request<Vocabulary>(fetchKeys.list(filter));
  } catch (error) {
    console.warn("Failed to fetch data.");
    return { count: 0, next: null, previous: null, results: [] };
  }
}

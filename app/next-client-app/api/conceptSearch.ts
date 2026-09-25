"use server";

import request from "@/lib/api/request";

const fetchKeys = {
  search: (filter?: string) =>
    filter ? `v2/omop/conceptsearch/?${filter}` : "v2/omop/conceptsearch/",
};

export async function searchConcepts(
  filter?: string | undefined,
): Promise<ConceptSearchResponse> {
  try {
    return await request<ConceptSearchResponse>(fetchKeys.search(filter));
  } catch (error) {
    console.warn("Failed to search concepts.");
    return {
      count: 0,
      results: [],
      facets: {
        vocabulary_id: {},
        domain_id: {},
        concept_class_id: {},
        standard_concept: {},
      },
    };
  }
}

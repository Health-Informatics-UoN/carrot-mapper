"use server";

import request from "@/lib/api/request";
import {
  unison_base_url,
  unison_api_key,
  recommendation_service,
} from "@/constants";
import { UnisonConceptResponse } from "@/types/recommendation";

export const getConceptRecommendationsUnison = async (
  // Unison can query by concept name, or concept code (exact match).
  // The latter is used first in searching, then the former.
  queryValue: string,
  domainId: string
): Promise<UnisonConceptResponse> => {
  try {
    if (recommendation_service === "unison") {
      const endpoint = `${queryValue}?apiKey=${unison_api_key}&domain=${domainId}`;
      return await request<UnisonConceptResponse>(endpoint, {
        baseUrl: unison_base_url,
        headers: {
          Accept: "application/json",
        },
      });
    }
    // TODO: Implement Lettuce recommendation service
    else if (recommendation_service === "lettuce") {
      console.log("Lettuce recommendation service");
    }

    throw new Error("Recommendation service not supported");
  } catch (error) {
    console.error("Error fetching recommendations:", error);
    throw error;
  }
};

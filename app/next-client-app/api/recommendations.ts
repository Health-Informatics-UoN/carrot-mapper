"use server";

import request from "@/lib/api/request";
import {
  unisonBaseUrl,
  unisonApiKey,
  recommendationService,
} from "@/constants";

export const getConceptRecommendationsUnison = async (
  // Unison can query by concept name, or concept code (exact match).
  // The latter is used first in searching, then the former.
  queryValue: string,
  domainId: string
): Promise<UnisonConceptResponse> => {
  try {
    if (recommendationService === "unison") {
      const endpoint = `${queryValue}?apiKey=${unisonApiKey}&domain=${domainId}`;
      return await request<UnisonConceptResponse>(endpoint, {
        baseUrl: unisonBaseUrl,
        headers: {
          Accept: "application/json",
        },
      });
    }
    // TODO: Implement Lettuce recommendation service
    else if (recommendationService === "lettuce") {
      console.log("Lettuce recommendation service");
    }

    throw new Error("Recommendation service not supported");
  } catch (error) {
    console.error("Error fetching recommendations:", error);
    throw error;
  }
};

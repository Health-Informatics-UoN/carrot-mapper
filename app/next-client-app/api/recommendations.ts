"use server";

import request from "@/lib/api/request";
import {
  unison_base_url,
  api_key_Unison,
  recommendation_service,
} from "@/constants";
import { UnisonConceptResponse } from "@/types/recommendation";

export const getConceptRecommendationsUnison = async (
  vocabCode: string
): Promise<UnisonConceptResponse> => {
  try {
    if (recommendation_service === "unison") {
      const endpoint = `${vocabCode}?apiKey=${api_key_Unison}`;
      return await request<UnisonConceptResponse>(endpoint, {
        baseUrl: unison_base_url,
        cache: "no-store",
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

"use server";

import request from "@/lib/api/request";
import {
  recommendationServiceBaseUrl,
  recommendationServiceApiKey,
  recommendationServiceName,
} from "@/constants";

export const getRecommendations = async (
  queryValue: string,
  domainId: string
): Promise<RecommendationServiceResponse> => {
  try {
    // Unison recommendation service
    // Unison can query by concept name, or concept code (exact match).
    // The latter is used first in searching, then the former.
    if (recommendationServiceName === "unison") {
      const endpoint = `${queryValue}?apiKey=${recommendationServiceApiKey}&domain=${domainId}`;
      return await request<RecommendationServiceResponse>(endpoint, {
        baseUrl: recommendationServiceBaseUrl,
        headers: {
          Accept: "application/json",
        },
      });
    }
    // Lettuce recommendation service
    if (recommendationServiceName === "lettuce") {
      const endpoint = `${queryValue}?domain=${domainId}`;
      return await request<RecommendationServiceResponse>(endpoint, {
        baseUrl: recommendationServiceBaseUrl,
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${recommendationServiceApiKey}`,
        },
        authMode: "apiKey",
      });
    }
    // Other recommendation services not supported
    throw new Error("Recommendation service not supported");
  } catch (error) {
    console.error("Error fetching recommendations:", error);
    throw error;
  }
};

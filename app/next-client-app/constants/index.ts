import { env } from "next-runtime-env";
import { MAX_FILE_SIZE_BYTES } from "./config";

export const apiUrl = process.env.BACKEND_URL;

export const recommendationService = process.env.RECOMMENDATION_SERVICE;

export const unisonBaseUrl = process.env.UNISON_BASE_URL;

export const unisonApiKey = process.env.UNISON_API_KEY;

export const enableReuseTriggerOption = env(
  "NEXT_PUBLIC_ENABLE_REUSE_TRIGGER_OPTION"
);

export const enableAIRecommendation = env(
  "NEXT_PUBLIC_ENABLE_AI_RECOMMENDATION"
);

export const enableStoredRecommendation = env(
  "NEXT_PUBLIC_ENABLE_STORED_RECOMMENDATION"
);

export const recommendationServiceName = env(
  "NEXT_PUBLIC_RECOMMENDATION_SERVICE_NAME"
);

// Re-export MAX_FILE_SIZE_BYTES from config.js
export { MAX_FILE_SIZE_BYTES };

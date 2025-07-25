import { env } from "next-runtime-env";

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

export const recommendationServiceName = env(
  "NEXT_PUBLIC_RECOMMENDATION_SERVICE_NAME"
);

// File size limit in bytes (30MB default)
export const MAX_FILE_SIZE_BYTES = 30 * 1024 * 1024;

// File size limit in MB for display
export const MAX_FILE_SIZE_MB = 30;

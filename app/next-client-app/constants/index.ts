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

// File size limit in bytes (configurable via env, default 30MB)
export const MAX_FILE_SIZE_BYTES = process.env.BODY_SIZE_LIMIT_MB
  ? parseInt(process.env.BODY_SIZE_LIMIT_MB, 10) * 1024 * 1024
  : 30 * 1024 * 1024;

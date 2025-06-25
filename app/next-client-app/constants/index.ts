import { env } from "next-runtime-env";

export const apiUrl = process.env.BACKEND_URL;

export const recommendation_service = process.env.RECOMMENDATION_SERVICE;

export const unison_base_url = process.env.UNISON_BASE_URL;

export const unison_api_key = process.env.UNISON_API_KEY;

export const enable_reuse_trigger_option = env(
  "NEXT_PUBLIC_ENABLE_REUSE_TRIGGER_OPTION"
);

export const enable_ai_recommendation = env(
  "NEXT_PUBLIC_ENABLE_AI_RECOMMENDATION"
);

export const recommendation_service_name = env(
  "NEXT_PUBLIC_RECOMMENDATION_SERVICE_NAME"
);

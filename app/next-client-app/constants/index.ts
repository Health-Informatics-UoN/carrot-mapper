import { env } from "next-runtime-env";
import { MAX_FILE_SIZE_BYTES } from "./config";

export const apiUrl = process.env.BACKEND_URL;

export const recommendationServiceBaseUrl =
  process.env.RECOMMENDATION_SERVICE_BASE_URL;

export const recommendationServiceApiKey =
  process.env.RECOMMENDATION_SERVICE_API_KEY;

export const enableReuseTriggerOption = env(
  "NEXT_PUBLIC_ENABLE_REUSE_TRIGGER_OPTION",
);

export const enableAIRecommendation = env(
  "NEXT_PUBLIC_ENABLE_AI_RECOMMENDATION",
);

export const enableStoredRecommendation = env(
  "NEXT_PUBLIC_ENABLE_STORED_RECOMMENDATION",
);

export const recommendationServiceName = env(
  "NEXT_PUBLIC_RECOMMENDATION_SERVICE",
);

// Re-export MAX_FILE_SIZE_BYTES from config.js
export { MAX_FILE_SIZE_BYTES };

// How a ScanReportConcept's `creation_type` maps to its label and
// explanation. Mirrors `CreationType` in app/api/mapping/models.py. Swatch
// colours live in ConceptColorLegend.tsx (next to the Tailwind classes they
// need to match, which must stay in a scanned `components/` path).
export const CONCEPT_CREATION_TYPES: Record<
  "V" | "M" | "R" | "X",
  { label: string; description: string }
> = {
  V: {
    label: "Vocab",
    description: "Matched via an OMOP vocabulary/code lookup",
  },
  M: {
    label: "Manual",
    description: "Added manually by entering a concept ID",
  },
  R: {
    label: "Reuse",
    description: "Reused from an existing mapping",
  },
  X: {
    label: "Matched",
    description: "Matched by exact text to a concept name",
  },
};

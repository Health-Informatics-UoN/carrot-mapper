import type { CSSProperties } from "react";
import type { SearchField, SearchFieldOption } from "../types/mapping-registry";

export const SEARCH_FIELDS: SearchFieldOption[] = [
  { value: "sourceTerm", label: "Source term" },
  { value: "conceptId", label: "OMOP concept ID" },
  { value: "mappingSet", label: "Mapping set" },
  { value: "vocabulary", label: "Vocabulary" },
  { value: "vocabularyVersion", label: "Vocabulary version" },
  { value: "canonicalIri", label: "Canonical IRI" },
  { value: "license", label: "License" },
  { value: "predicate", label: "Predicate" },
  { value: "justification", label: "Justification" },
];

export const SET_SEARCH_FIELDS: SearchFieldOption[] = [
  { value: "mappingSet", label: "Mapping set title" },
  { value: "publisher", label: "Published by" },
  { value: "mappingSetVersion", label: "Version" },
  { value: "license", label: "License" },
];

// Examples cycled through the search placeholder for each field.
export const SEARCH_EXAMPLES: Record<SearchField, string[]> = {
  sourceTerm: ["diabetes", "hypertension", "asthma", "chronic kidney disease"],
  conceptId: ["201820", "317009", "316866"],
  mappingSet: ["Clinical terminology", "Community OMOP mappings"],
  vocabulary: ["SNOMED"],
  vocabularyVersion: ["2025-09"],
  canonicalIri: ["example.org/terms/diabetes"],
  license: ["CC-BY-4.0", "CC0-1.0"],
  predicate: ["skos:exactMatch", "skos:closeMatch"],
  justification: ["ManualMappingCuration", "LexicalMatching"],
  publisher: ["Researcher A", "Researcher C"],
  mappingSetVersion: ["1.0.0", "1.2.0"],
};

export const PAGE_SIZE_OPTIONS = [10, 20, 30, 40, 50];
export const DEFAULT_PAGE_SIZE = 10;
export const SEARCH_DEBOUNCE_MS = 350;

// Carrot artwork only; the cloud, title, tagline and label are drawn in code
// (components/registry/registry-logo.tsx) on the same canvas.
export const CARROT_SRC = "/mapper-registry-carrot.svg";
// Size of the logo canvas shared by the carrot SVG and the code-drawn parts.
// These set the aspect ratio; the rendered size comes from the h-* classes.
export const LOGO_WIDTH = 565;
export const LOGO_HEIGHT = 660;

// Keeps the dialogs fading/zooming in place instead of sliding in from the top-left.
export const STATIC_DIALOG_STYLE = {
  "--tw-enter-translate-x": "0px",
  "--tw-enter-translate-y": "0px",
  "--tw-exit-translate-x": "0px",
  "--tw-exit-translate-y": "0px",
} as CSSProperties;

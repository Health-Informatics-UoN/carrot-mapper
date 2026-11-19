export type SearchField =
  | "sourceTerm"
  | "conceptId"
  | "mappingSet"
  | "vocabulary"
  | "vocabularyVersion"
  | "canonicalIri"
  | "license"
  | "predicate"
  | "justification"
  | "publisher"
  | "mappingSetVersion";

export type SearchFieldOption = { value: SearchField; label: string };

export type Mapping = {
  id: string;
  mappingSetId: string;
  sourceTerm: string;
  subjectId: string;
  canonicalIri: string;
  targetConcept: string;
  conceptId: string;
  vocabulary: string;
  vocabularyVersion: string;
  publisher: string;
  mappingSet: string;
  mappingSetVersion: string;
  predicate: string;
  justification: string;
  license: string;
  publishedAt: string;
};

export type MappingSet = {
  id: string;
  title: string;
  version: string;
  publisher: string;
  license: string;
  publishedAt: string;
  description: string;
  mappings: Mapping[];
};

export type View = "mappings" | "sets";

export type Sort = { key: string; direction: "asc" | "desc" } | null;

export type RegistryStats = {
  totalMappings: number;
  totalSets: number;
};

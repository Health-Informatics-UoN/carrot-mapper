interface RecommendationItem {
  accuracy: number | null;
  conceptId: number;
  conceptName: string;
  conceptCode: string;
  vocabulary: string;
  domain: string;
  conceptClass: string;
  explanation: string;
  standardConcept?: string;
  scores?: { "vector-search": number };
}

interface RecommendationMetadata {
  assistant: string;
  version: string;
  pipeline: string;
  info: string | null;
}

interface RecommendationServiceResponse {
  items: RecommendationItem[];
  count?: number;
  metadata?: RecommendationMetadata;
}

interface MappingRecommendation {
  id: number;
  content_type: number;
  object_id: number;
  concept: ConceptDetail;
  score: number | null;
  tool_name: string;
  tool_version: string;
  created_at: Date;
}

import request from '@/lib/api/request';
import { recommendation_service_url } from '@/constants';


// - This should be moved to types

// Define the interface for the concept recommendation response
export interface ConceptRecommendation {
  conceptCode: string;     // Code of the recommended concept
  conceptName: string;     // Name of the recommended concept
  matchScore: number;      // Score indicating how good the match is (0-1)
  recommendedBy: string;   // System or algorithm that made the recommendation
  metricsUsed: string;   // Metrics or factors used to make this recommendation
}

export const getConceptRecommendations = async (
  vocabCode: string
): Promise<ConceptRecommendation[]> => {

  console.log(`Fetching recommendations for code: ${vocabCode}`);
  console.log(`Using service URL: ${recommendation_service_url || 'undefined'}`);

  try {
    return await request<ConceptRecommendation[]>(`concepts/recommendations`, {
      requireAuth: false,
      baseUrl: recommendation_service_url,
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ code: vocabCode })
    });
    
  } catch (error) {
    console.error('Error fetching recommendations:', error);
    throw error;
  }
};

/// - Mocks the API Response 

export const getMockRecommendations = (vocabCode: string): ConceptRecommendation[] => {
  return [
    // Example 1
      {
        conceptCode: "SNOMED-73211009",
        conceptName: "Diabetes mellitus",
        matchScore: 0.96,
        recommendedBy: "Lettuce AI",
        metricsUsed: "Semantic Similarity"
      },
      {
        conceptCode: "ICD10-I21.3",
        conceptName: "ST elevation myocardial infarction",
        matchScore: 0.89,
        recommendedBy: "Lettuce AI",
        metricsUsed: "Terminology Mapping"
      },
      {
        conceptCode: "LOINC-8480-6",
        conceptName: "Systolic blood pressure",
        matchScore: 0.92,
        recommendedBy: "Lettuce AI",
        metricsUsed: "Ontology Alignment"
      },
      {
        conceptCode: "RxNorm-1049502",
        conceptName: "Acetaminophen 325 MG Oral Tablet",
        matchScore: 0.78,
        recommendedBy: "Lettuce AI",
        metricsUsed: "Drug Name Recognition"
      },
      {
        conceptCode: "UMLS-C0002871",
        conceptName: "Anemia, Iron-Deficiency",
        matchScore: 0.87,
        recommendedBy: "Lettuce AI",
        metricsUsed: "Medical Entity Recognition"
      }
  ];
};
import { objToQuery } from "@/lib/client-utils";
import { searchConcepts } from "@/api/conceptSearch";
import { ConceptSearchResultsTable } from "@/components/concepts/search/ConceptSearchResultsTable";

interface ConceptSearchTabProps {
  searchParams: ConceptSearchParameters;
}

export async function ConceptSearchTab({
  searchParams,
}: ConceptSearchTabProps) {
  const query = searchParams.q?.trim() ?? "";

  const combinedParams = {
    query,
    vocabulary_id: searchParams.vocabulary_id,
    domain_id: searchParams.domain_id,
    concept_class_id: searchParams.concept_class_id,
    standard_concept: searchParams.standard_concept,
    p: searchParams.search_p,
    page_size: searchParams.search_page_size ?? 20,
  };
  const response = await searchConcepts(objToQuery(combinedParams));

  return (
    <ConceptSearchResultsTable
      results={response.results}
      count={response.count}
      facets={response.facets}
      hasQuery={query.length > 0}
    />
  );
}

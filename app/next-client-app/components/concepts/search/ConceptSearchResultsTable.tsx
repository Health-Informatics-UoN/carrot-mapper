"use client";

import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { columns } from "./columns";
import { ConceptSearchBox } from "./ConceptSearchBox";
import { ConceptSearchFacetFilter } from "./ConceptSearchFacetFilter";

interface ConceptSearchResultsTableProps {
  results: ConceptSearchResult[];
  count: number;
  facets: ConceptSearchFacets;
  hasQuery: boolean;
}

export function ConceptSearchResultsTable({
  results,
  count,
  facets,
  hasQuery,
}: ConceptSearchResultsTableProps) {
  const filter = (
    <div className="flex flex-wrap gap-2 items-center">
      <ConceptSearchBox />
      <ConceptSearchFacetFilter
        title="Vocabulary"
        param="vocabulary_id"
        counts={facets.vocabulary_id}
      />
      <ConceptSearchFacetFilter
        title="Domain"
        param="domain_id"
        counts={facets.domain_id}
      />
      <ConceptSearchFacetFilter
        title="Class"
        param="concept_class_id"
        counts={facets.concept_class_id}
      />
      <ConceptSearchFacetFilter
        title="Standard"
        param="standard_concept"
        counts={facets.standard_concept}
      />
    </div>
  );

  if (!hasQuery) {
    return (
      <div className="space-y-2">
        {filter}
        <EmptyState
          icon="library"
          title="Search the OMOP vocabulary"
          description="Type a concept name, code, or synonym above to get started."
        />
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {results.length > 0 ? (
        <DataTable
          columns={columns}
          data={results}
          count={count}
          Filter={filter}
          defaultPageSize={20}
          pageParam="search_p"
          pageSizeParam="search_page_size"
        />
      ) : (
        <div className="space-y-2">
          {filter}
          <EmptyState
            icon="library"
            title="No concepts found"
            description="Try a different search term or adjust your filters."
          />
        </div>
      )}
    </div>
  );
}

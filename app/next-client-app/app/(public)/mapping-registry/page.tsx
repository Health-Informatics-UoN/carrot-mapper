"use client";

import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MappingDetailsDialog } from "@/components/registry/mapping-details-dialog";
import { MappingSetDetailsDialog } from "@/components/registry/mapping-set-details-dialog";
import { RegistryDataContent } from "@/components/registry/registry-data-content";
import { RegistryHero } from "@/components/registry/registry-hero";
import { RegistryLandingActions } from "@/components/registry/registry-landing-actions";
import { RegistryResults } from "@/components/registry/registry-results";
import { RegistrySearchBar } from "@/components/registry/registry-search-bar";
import { useRegistrySearch } from "@/lib/hooks/use-registry-search";
import type { Mapping, MappingSet } from "@/types/mapping-registry";

export default function RegistryPage() {
  const registry = useRegistrySearch();
  const [selectedMapping, setSelectedMapping] = useState<Mapping | null>(null);
  const [selectedSet, setSelectedSet] = useState<MappingSet | null>(null);
  const [mappingToReturn, setMappingToReturn] = useState<Mapping | null>(null);

  function openSetForMapping(mapping: Mapping) {
    const mappingSet = registry.setForMapping(mapping);
    if (!mappingSet) return;
    setMappingToReturn(mapping);
    setSelectedMapping(null);
    setSelectedSet(mappingSet);
  }

  function openMappingFromSet(mapping: Mapping) {
    setSelectedSet(null);
    setMappingToReturn(null);
    setSelectedMapping(mapping);
  }

  function returnToMapping() {
    if (!mappingToReturn) return;
    setSelectedSet(null);
    setSelectedMapping(mappingToReturn);
    setMappingToReturn(null);
  }

  return (
    <div className="relative flex w-full flex-1 flex-col pb-3">
      {/* Keep the stats card at the top-right without covering results while scrolling. */}
      <div className="flex justify-end pt-3 md:-mr-4 lg:absolute lg:-right-4 lg:top-0 lg:z-10 lg:mr-0 lg:pt-0">
        <RegistryDataContent stats={registry.stats} />
      </div>

      {/* Landing: a 3-row grid (1fr / auto / 1fr) keeps the search bar on the
          vertical centre line. Results: a plain compact block. */}
      <div
        className={
          registry.showResults
            ? "mx-auto w-full max-w-3xl pt-4 pb-5"
            : "mx-auto grid w-full max-w-3xl flex-1 grid-rows-[1fr_auto_1fr] py-6"
        }
      >
        <RegistryHero compact={registry.showResults} />

        <RegistrySearchBar
          view={registry.view}
          field={registry.field}
          query={registry.query}
          isLoading={registry.isLoading}
          onFieldChange={registry.changeField}
          onQueryChange={registry.changeQuery}
        />

        {registry.showResults ? (
          <div className="mt-4 flex justify-center">
            <Button type="button" variant="outline" onClick={registry.reset}>
              <ArrowLeft className="size-4" /> Back to Registry
            </Button>
          </div>
        ) : (
          <RegistryLandingActions onBrowse={registry.browse} />
        )}
      </div>

      {registry.showResults && (
        <RegistryResults
          view={registry.view}
          query={registry.query}
          isLoading={registry.isLoading}
          mappings={registry.mappings}
          mappingSets={registry.mappingSets}
          total={registry.total}
          page={registry.page}
          pageSize={registry.pageSize}
          sort={registry.sort}
          onSortChange={registry.setSort}
          onPageChange={registry.setPage}
          onPageSizeChange={registry.changePageSize}
          onViewChange={registry.chooseView}
          onBrowse={registry.browse}
          onViewMapping={setSelectedMapping}
          onViewSet={setSelectedSet}
        />
      )}

      <MappingDetailsDialog
        mapping={selectedMapping}
        onClose={() => setSelectedMapping(null)}
        onViewSet={openSetForMapping}
      />

      <MappingSetDetailsDialog
        mappingSet={selectedSet}
        onClose={() => {
          setSelectedSet(null);
          setMappingToReturn(null);
        }}
        onBackToMapping={mappingToReturn ? returnToMapping : undefined}
        onSelectMapping={openMappingFromSet}
      />
    </div>
  );
}

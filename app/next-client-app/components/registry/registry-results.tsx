import { useMemo } from "react";
import { Search } from "lucide-react";
import { DataTable } from "@/components/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Mapping, MappingSet, Sort, View } from "@/types/mapping-registry";
import { getMappingColumns } from "./mapping-columns";
import { getMappingSetColumns } from "./mapping-set-columns";
import { RegistryResultsLoading } from "./registry-results-loading";
import { RegistryTablePagination } from "./registry-table-pagination";

type RegistryResultsProps = {
  view: View;
  query: string;
  isLoading: boolean;
  /** Current page of mappings. */
  mappings: Mapping[];
  /** Current page of mapping sets. */
  mappingSets: MappingSet[];
  /** Total matching records across all pages, for the active view. */
  total: number;
  page: number;
  pageSize: number;
  sort: Sort;
  onSortChange: (sort: Sort) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
  onViewChange: (view: View) => void;
  onBrowse: (view: View) => void;
  onViewMapping: (mapping: Mapping) => void;
  onViewSet: (mappingSet: MappingSet) => void;
};

export function RegistryResults({
  view,
  query,
  isLoading,
  mappings,
  mappingSets,
  total,
  page,
  pageSize,
  sort,
  onSortChange,
  onPageChange,
  onPageSizeChange,
  onViewChange,
  onBrowse,
  onViewMapping,
  onViewSet,
}: RegistryResultsProps) {
  const mappingColumns = useMemo(
    () => getMappingColumns({ sort, onSort: onSortChange, onView: onViewMapping }),
    [sort, onSortChange, onViewMapping],
  );
  const mappingSetColumns = useMemo(
    () => getMappingSetColumns({ sort, onSort: onSortChange, onView: onViewSet }),
    [sort, onSortChange, onViewSet],
  );

  const trimmedQuery = query.trim();
  const isMappings = view === "mappings";
  const noun = isMappings ? "published mapping" : "mapping set";

  return (
    <section className="mx-auto w-full max-w-7xl space-y-4 pb-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">
            {isMappings ? "Mapping search results" : "Published mapping sets"}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {isLoading ? "Searching..." : `${total} ${noun}${total === 1 ? "" : "s"}`}
            {trimmedQuery && !isLoading ? ` for “${trimmedQuery}”` : ""}
            {isMappings && !isLoading ? " · One row per published mapping" : ""}
          </p>
        </div>
        <Badge variant="outline">Demo data — no API calls</Badge>
      </div>

      <div className="flex gap-2 border-b pb-2" role="tablist" aria-label="Registry results type">
        <Button
          type="button"
          role="tab"
          aria-selected={isMappings}
          size="sm"
          variant={isMappings ? "secondary" : "ghost"}
          onClick={() => onViewChange("mappings")}
        >
          Mappings
        </Button>
        <Button
          type="button"
          role="tab"
          aria-selected={!isMappings}
          size="sm"
          variant={!isMappings ? "secondary" : "ghost"}
          onClick={() => onViewChange("sets")}
        >
          Mapping Sets
        </Button>
      </div>

      {isLoading ? (
        <RegistryResultsLoading />
      ) : total > 0 ? (
        <>
          {isMappings ? (
            <DataTable key="mappings" columns={mappingColumns} data={mappings} count={total} paginated={false} />
          ) : (
            <DataTable key="sets" columns={mappingSetColumns} data={mappingSets} count={total} paginated={false} />
          )}
          <RegistryTablePagination
            page={page}
            pageSize={pageSize}
            count={total}
            onPageChange={onPageChange}
            onPageSizeChange={onPageSizeChange}
          />
        </>
      ) : (
        <div className="rounded-lg border border-dashed px-6 py-12 text-center">
          <Search className="mx-auto mb-3 size-9 text-muted-foreground" />
          <h3 className="font-semibold">No matching {isMappings ? "mappings" : "mapping sets"}</h3>
          <p className="mt-2 text-sm text-muted-foreground">Try a different search term or search field.</p>
          <Button className="mt-4" variant="outline" onClick={() => onBrowse(view)}>
            Browse all {isMappings ? "mappings" : "mapping sets"}
          </Button>
        </div>
      )}
    </section>
  );
}

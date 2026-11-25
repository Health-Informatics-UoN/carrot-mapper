import { useMemo } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import type { Mapping, MappingSet, Sort, View } from "@/types/mapping-registry";
import { getMappingColumns } from "./mapping-columns";
import { getMappingSetColumns } from "./mapping-set-columns";
import { RegistryResultsLoading } from "./registry-results-loading";

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
  sort: Sort;
  onSortChange: (sort: Sort) => void;
  onBrowse: (view: View) => void;
};

export function RegistryResults({
  view,
  query,
  isLoading,
  mappings,
  mappingSets,
  total,
  sort,
  onSortChange,
  onBrowse,
}: RegistryResultsProps) {
  const mappingColumns = useMemo(
    () => getMappingColumns({ sort, onSort: onSortChange }),
    [sort, onSortChange],
  );
  const mappingSetColumns = useMemo(
    () => getMappingSetColumns({ sort, onSort: onSortChange }),
    [sort, onSortChange],
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
            {isLoading
              ? "Searching..."
              : `${total} ${noun}${total === 1 ? "" : "s"}`}
            {trimmedQuery && !isLoading ? ` for “${trimmedQuery}”` : ""}
            {isMappings && !isLoading ? " · One row per published mapping" : ""}
          </p>
        </div>
      </div>

      <nav
        className="flex gap-2 border-b pb-2"
        aria-label="Registry results type"
      >
        <Button asChild size="sm" variant={isMappings ? "secondary" : "ghost"}>
          <Link
            href="/registry/mappings"
            aria-current={isMappings ? "page" : undefined}
          >
            Mappings
          </Link>
        </Button>
        <Button asChild size="sm" variant={!isMappings ? "secondary" : "ghost"}>
          <Link
            href="/registry/mapping-sets"
            aria-current={!isMappings ? "page" : undefined}
          >
            Mapping Sets
          </Link>
        </Button>
      </nav>

      {isLoading ? (
        <RegistryResultsLoading />
      ) : total > 0 ? (
        <>
          {isMappings ? (
            <DataTable
              key="mappings"
              columns={mappingColumns}
              data={mappings}
              count={total}
              paginated
            />
          ) : (
            <DataTable
              key="sets"
              columns={mappingSetColumns}
              data={mappingSets}
              count={total}
              paginated
            />
          )}
        </>
      ) : (
        <div className="rounded-lg border border-dashed px-6 py-12 text-center">
          <Search className="mx-auto mb-3 size-9 text-muted-foreground" />
          <h3 className="font-semibold">
            No matching {isMappings ? "mappings" : "mapping sets"}
          </h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Try a different search term or search field.
          </p>
          <Button
            className="mt-4"
            variant="outline"
            onClick={() => onBrowse(view)}
          >
            Browse all {isMappings ? "mappings" : "mapping sets"}
          </Button>
        </div>
      )}
    </section>
  );
}

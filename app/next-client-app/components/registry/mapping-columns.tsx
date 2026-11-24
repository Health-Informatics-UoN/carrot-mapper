import Link from "next/link";
import type { ColumnDef, HeaderContext } from "@tanstack/react-table";
import { ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Mapping, Sort } from "@/types/mapping-registry";
import { RegistrySortHeader } from "./registry-sort-header";

type MappingColumnsOptions = {
  sort: Sort;
  onSort: (sort: Sort) => void;
};

export function getMappingColumns({
  sort,
  onSort,
}: MappingColumnsOptions): ColumnDef<Mapping>[] {
  const sortableHeader = (
    title: string,
    sortKey: keyof Mapping,
  ): ColumnDef<Mapping>["header"] =>
    function SortableHeader({ column }: HeaderContext<Mapping, unknown>) {
      return (
        <RegistrySortHeader
          column={column}
          title={title}
          sortKey={sortKey}
          sort={sort}
          onSort={onSort}
        />
      );
    };

  return [
    {
      accessorKey: "sourceTerm",
      header: sortableHeader("Source term", "sourceTerm"),
      cell: ({ row }) => (
        <span className="font-medium">{row.original.sourceTerm}</span>
      ),
    },
    {
      accessorKey: "targetConcept",
      header: sortableHeader("Target concept", "targetConcept"),
    },
    {
      accessorKey: "conceptId",
      header: sortableHeader("Concept ID", "conceptId"),
      cell: ({ row }) => (
        <span className="font-mono text-xs">{row.original.conceptId}</span>
      ),
    },
    {
      accessorKey: "vocabulary",
      header: sortableHeader("Vocabulary", "vocabulary"),
    },
    {
      accessorKey: "publisher",
      header: sortableHeader("Published by", "publisher"),
    },
    {
      accessorKey: "mappingSet",
      header: sortableHeader("Mapping set", "mappingSet"),
      cell: ({ row }) => (
        <div className="max-w-52 whitespace-normal">
          {row.original.mappingSet}
          <span className="block text-xs text-muted-foreground">
            v{row.original.mappingSetVersion}
          </span>
        </div>
      ),
    },
    {
      id: "details",
      header: () => (
        <div className="text-right text-sm font-semibold sm:text-base">
          Details
        </div>
      ),
      enableHiding: false,
      enableSorting: false,
      cell: ({ row }) => (
        <div className="text-right">
          <Button asChild size="sm" variant="outline">
            <Link
              href={`/registry/mappings/${row.original.id}`}
              onClick={() => {
                try {
                  sessionStorage.setItem(
                    "registry:lastMappingsUrl",
                    window.location.pathname + window.location.search,
                  );
                } catch {}
              }}
              aria-label={`View details for ${row.original.sourceTerm}, ${row.original.publisher}`}
            >
              View <ChevronRight className="size-4" />
            </Link>
          </Button>
        </div>
      ),
    },
  ];
}

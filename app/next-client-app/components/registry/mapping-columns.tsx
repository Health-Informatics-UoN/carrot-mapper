import Link from "next/link";
import type { ColumnDef, HeaderContext } from "@tanstack/react-table";
import { ChevronRight } from "lucide-react";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { Button } from "@/components/ui/button";
import { RESULTS_URL_KEYS } from "@/constants/mapping-registry";
import type { Mapping } from "@/types/mapping-registry";
import { rememberResultsUrl } from "./back-to-results-link";

export function getMappingColumns(): ColumnDef<Mapping>[] {
  const sortableHeader = (
    title: string,
    sortName: string,
  ): ColumnDef<Mapping>["header"] =>
    function SortableHeader({ column }: HeaderContext<Mapping, unknown>) {
      return (
        <DataTableColumnHeader
          column={column}
          title={title}
          sortName={sortName}
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
      header: ({ column }) => (
        <DataTableColumnHeader
          column={column}
          title="Details"
          className="flex h-8 items-center justify-end text-sm font-medium"
        />
      ),
      enableHiding: false,
      enableSorting: false,
      cell: ({ row }) => (
        <div className="text-right">
          <Button asChild size="sm" variant="outline">
            <Link
              href={`/registry/mappings/${row.original.id}`}
              onClick={() => rememberResultsUrl(RESULTS_URL_KEYS.mappings)}
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

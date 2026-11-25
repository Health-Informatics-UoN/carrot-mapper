import Link from "next/link";
import type { ColumnDef, HeaderContext } from "@tanstack/react-table";
import { ChevronRight } from "lucide-react";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { Button } from "@/components/ui/button";
import type { MappingSet } from "@/types/mapping-registry";

export function getMappingSetColumns(): ColumnDef<MappingSet>[] {
  const sortableHeader = (
    title: string,
    sortName: string,
  ): ColumnDef<MappingSet>["header"] =>
    function SortableHeader({ column }: HeaderContext<MappingSet, unknown>) {
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
      accessorKey: "title",
      header: sortableHeader("Mapping set", "title"),
      cell: ({ row }) => (
        <span className="font-medium">{row.original.title}</span>
      ),
    },
    {
      accessorKey: "publisher",
      header: sortableHeader("Published by", "publisher"),
    },
    {
      accessorKey: "version",
      header: sortableHeader("Version", "version"),
    },
    {
      accessorKey: "license",
      header: sortableHeader("License", "license"),
    },
    {
      accessorKey: "publishedAt",
      header: sortableHeader("Published", "publishedAt"),
    },
    {
      id: "mappingCount",
      header: () => (
        <span className="text-sm font-semibold sm:text-base">Mappings</span>
      ),
      enableSorting: false,
      cell: ({ row }) => (
        <span className="tabular-nums">{row.original.mappings.length}</span>
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
              href={`/registry/mapping-sets/${row.original.id}`}
              onClick={() => {
                try {
                  sessionStorage.setItem(
                    "registry:lastMappingSetsUrl",
                    window.location.pathname + window.location.search,
                  );
                } catch {}
              }}
              aria-label={`View details for ${row.original.title}, ${row.original.publisher}`}
            >
              View <ChevronRight className="size-4" />
            </Link>
          </Button>
        </div>
      ),
    },
  ];
}

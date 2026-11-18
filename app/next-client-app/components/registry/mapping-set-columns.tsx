import type { ColumnDef, HeaderContext } from "@tanstack/react-table";
import { ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { MappingSet, Sort } from "@/types/mapping-registry";
import { RegistrySortHeader } from "./registry-sort-header";

type MappingSetColumnsOptions = {
  sort: Sort;
  onSort: (sort: Sort) => void;
  onView: (mappingSet: MappingSet) => void;
};

export function getMappingSetColumns({ sort, onSort, onView }: MappingSetColumnsOptions): ColumnDef<MappingSet>[] {
  const sortableHeader =
    (title: string, sortKey: keyof MappingSet): ColumnDef<MappingSet>["header"] =>
    function SortableHeader({ column }: HeaderContext<MappingSet, unknown>) {
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
      accessorKey: "title",
      header: sortableHeader("Mapping set", "title"),
      cell: ({ row }) => <span className="font-medium">{row.original.title}</span>,
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
      header: () => <span className="text-sm font-semibold sm:text-base">Mappings</span>,
      enableSorting: false,
      cell: ({ row }) => <span className="tabular-nums">{row.original.mappings.length}</span>,
    },
    {
      id: "details",
      header: () => <div className="text-right text-sm font-semibold sm:text-base">Details</div>,
      enableHiding: false,
      enableSorting: false,
      cell: ({ row }) => (
        <div className="text-right">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => onView(row.original)}
            aria-label={`View details for ${row.original.title}, ${row.original.publisher}`}
          >
            View <ChevronRight className="size-4" />
          </Button>
        </div>
      ),
    },
  ];
}

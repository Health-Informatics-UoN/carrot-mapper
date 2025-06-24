"use client";

import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { UnisonConceptItem } from "@/types/recommendation";
import { Button } from "../ui/button";

export const columns = (
  tableId: string,
  rowId: number,
  onApplySuggestion: (data: {
    concept: number;
    object_id: number;
    content_type: string;
    creation_type: string;
    table_id: string;
  }) => void
): ColumnDef<UnisonConceptItem>[] => [
  {
    id: "Concept Name",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Concept Name" />
    ),
    accessorKey: "conceptName",
    enableSorting: false,
    enableHiding: true,
  },
  {
    id: "Concept ID",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Concept ID" />
    ),
    accessorKey: "conceptId",
    cell: ({ row }) => {
      const { conceptId } = row.original;
      return (
        <a
          className="text-blue-500 underline"
          target="_blank"
          href={`https://athena.ohdsi.org/search-terms/terms/${conceptId}`}
        >
          {conceptId}
        </a>
      );
    },
    enableSorting: false,
    enableHiding: true,
  },
  {
    id: "Vocabulary",
    accessorKey: "vocabulary",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Vocabulary" />
    ),
    enableSorting: false,
    enableHiding: true,
  },
  {
    id: "Domain",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Domain" />
    ),
    enableSorting: false,
    enableHiding: true,
    accessorKey: "domain",
  },
  {
    id: "Action",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Action" />
    ),
    cell: ({ row }) => {
      const { conceptId } = row.original;
      return (
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            onApplySuggestion({
              concept: conceptId,
              object_id: rowId,
              content_type: "scanreportvalue",
              creation_type: "M",
              table_id: tableId,
            });
          }}
        >
          Add
        </Button>
      );
    },
    enableSorting: false,
    enableHiding: true,
  },
];

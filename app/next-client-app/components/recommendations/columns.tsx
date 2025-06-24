"use client";

import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { UnisonConceptItem } from "@/types/recommendation";

export const columns: ColumnDef<UnisonConceptItem>[] = [
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
    id: "Concept Class",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Concept Class" />
    ),
    accessorKey: "conceptClass",
    enableSorting: false,
    enableHiding: true,
  },
];

"use client";

import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { ColumnDef } from "@tanstack/react-table";

export const columns: ColumnDef<Vocabulary>[] = [
  {
    id: "Vocabulary ID",
    accessorKey: "vocabulary_id",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Vocabulary ID"
        sortName="vocabulary_id"
      />
    ),
    enableHiding: true,
    enableSorting: true,
  },
  {
    id: "Name",
    accessorKey: "vocabulary_name",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Name"
        sortName="vocabulary_name"
      />
    ),
    enableHiding: true,
    enableSorting: true,
  },
  {
    id: "Version",
    accessorKey: "vocabulary_version",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Version"
        sortName="vocabulary_version"
      />
    ),
    enableHiding: true,
    enableSorting: true,
  },
  {
    id: "Reference",
    accessorKey: "vocabulary_reference",
    header: "Reference",
    enableHiding: true,
    enableSorting: false,
  },
];

"use client";

import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { ColumnDef } from "@tanstack/react-table";
import { format } from "date-fns/format";

export const columns: ColumnDef<DataSet>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Name" sortName="name" />
    ),
    enableHiding: true,
    enableSorting: true,
  },
  {
    id: "Creation Date",
    accessorKey: "created_at",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Creation Date"
        sortName="created_at"
      />
    ),
    enableHiding: true,
    enableSorting: true,
    cell: ({ row }) => {
      const date = new Date(row.original.created_at);
      return format(date, "d MMM HH:mm");
    },
  },
  {
    id: "Data Partner",
    accessorKey: "data_partner.name",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Data Partner" />
    ),
    enableHiding: true,
    enableSorting: false,
  },
];

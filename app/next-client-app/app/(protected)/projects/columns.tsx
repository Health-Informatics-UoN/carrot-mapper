"use client";

import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { Button } from "@/components/ui/button";
import { ColumnDef } from "@tanstack/react-table";
import { format } from "date-fns/format";
import Link from "next/link";

export const columns: ColumnDef<Project>[] = [
  {
    id: "Name",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Name" sortName="name" />
    ),
    enableHiding: true,
    enableSorting: true,
    cell: ({ row }) => {
      const { id, name } = row.original;
      return (
        <Link href={`/projects/${id}/`}>
          <Button
            variant="link"
            className="font-bold"
          >
            {name}
          </Button>
        </Link>
      );
    }
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
      return format(date, "MMM dd, yyyy h:mm a");
    }
  }
];

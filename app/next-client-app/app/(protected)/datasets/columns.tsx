"use client";

import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { ColumnDef } from "@tanstack/react-table";
import { MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { EyeNoneIcon, EyeOpenIcon, Pencil2Icon } from "@radix-ui/react-icons";
import { format } from "date-fns/format";
import Link from "next/link";
import { HandleArchive } from "@/components/core/HandleArchive";

export const columns: ColumnDef<DataSet>[] = [
  {
    accessorKey: "id",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="ID" sortName="id" />
    ),
    enableHiding: false,
    enableSorting: true
  },
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
        <Link href={`/datasets/${id}/`}>
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
    id: "Data Partner",
    accessorKey: "data_partner",
    accessorFn: (row) => row.data_partner.name,
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Data Partner"
        sortName="data_partner"
      />
    ),
    enableHiding: true,
    enableSorting: true
  },
  {
    accessorKey: "visibility",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Visibility"
        sortName="visibility"
      />
    ),
    enableHiding: true,
    enableSorting: true,
    // Show Shared Visibility or Restricted Visibility
    cell: ({ row }) => (
      <span>
        {row.original.visibility === "PUBLIC" ? "Shared" : "Restricted"}
      </span>
    )
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
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const { id, hidden } = row.original;

      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <span className="sr-only">Open menu</span>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <Link href={`/datasets/${id}/details/`} prefetch={false}>
              <DropdownMenuItem>
                Details <Pencil2Icon className="ml-auto" />
              </DropdownMenuItem>
            </Link>
            <DropdownMenuItem
              onClick={() =>
                HandleArchive({
                  id: id,
                  hidden: hidden,
                  ObjName: row.original.name,
                  type: "datasets"
                })
              }
            >
              {hidden ? "Unarchive" : "Archive"}
              {hidden ? (
                <EyeOpenIcon className="ml-auto" />
              ) : (
                <EyeNoneIcon className="ml-auto" />
              )}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => navigator.clipboard.writeText(row.original.name)}
            >
              Copy Dataset's Name
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );
    },
    header: "Actions",
    enableHiding: false
  }
];

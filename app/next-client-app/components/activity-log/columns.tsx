"use client";

import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { Badge } from "@/components/ui/badge";
import { format } from "date-fns/format";
import {
  ACTIVITY_LOG_VERB_LABELS,
  describeActivityLogDetail,
} from "./ActivityLogUtils";

export const columns: ColumnDef<ActivityLog>[] = [
  {
    id: "Occurred",
    accessorKey: "occurred_at",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Occurred" />
    ),
    cell: ({ row }) => format(row.original.occurred_at, "d MMM HH:mm"),
    enableHiding: true,
    enableSorting: false,
  },
  {
    id: "Event",
    accessorKey: "verb",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Event" />
    ),
    cell: ({ row }) => (
      <Badge variant="outline">
        {ACTIVITY_LOG_VERB_LABELS[row.original.verb] ?? row.original.verb}
      </Badge>
    ),
    enableHiding: true,
    enableSorting: false,
  },
  {
    id: "User",
    accessorKey: "actor_label",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="User" />
    ),
    cell: ({ row }) => row.original.actor_label || "—",
    enableHiding: true,
    enableSorting: false,
  },
  {
    id: "Details",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Details" />
    ),
    cell: ({ row }) => describeActivityLogDetail(row.original),
    enableHiding: true,
    enableSorting: false,
  },
];

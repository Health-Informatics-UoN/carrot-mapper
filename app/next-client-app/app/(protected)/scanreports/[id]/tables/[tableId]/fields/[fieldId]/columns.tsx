"use client";
import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { ConceptTags } from "@/components/concepts/concept-tags";
import AddConcept from "@/components/concepts/add-concept";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import CopyButton from "@/components/core/CopyButton";

export const columns = (
  addSR: (concept: ScanReportConcept, c: Concept) => void,
  deleteSR: (id: number) => void,
  tableId: string
): ColumnDef<ScanReportValue>[] => [
  {
    id: "Value",
    accessorKey: "value",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Value" sortName="value" />
    ),
    enableHiding: true,
    enableSorting: false,
    cell: ({ row }) => {
      const { value } = row.original;

      return (
        <div className="flex items-center gap-2">
          <span className="font-bold">{value}</span>
          <CopyButton textToCopy={value} />
        </div>
      );
    }
  },
  {
    id: "Value Description",
    accessorKey: "value_description",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Value Description"
        sortName="value_description"
      />
    ),
    enableHiding: true,
    enableSorting: false
  },
  {
    id: "Frequency",
    accessorKey: "frequency",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Frequency"
        sortName="frequency"
      />
    ),
    enableHiding: true,
    enableSorting: false
  },
  {
    id: "Concepts",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Concepts" />
    ),
    enableHiding: true,
    enableSorting: false,
    cell: ({ row }) => {
      const { concepts } = row.original;
      return (
        <Suspense fallback={<Skeleton className="h-5 w-[250px]" />}>
          <ConceptTags concepts={concepts ?? []} deleteSR={deleteSR} />
        </Suspense>
      );
    }
  },
  {
    id: "Add Concept",
    header: "",
    cell: ({ row }) => {
      const { id, permissions } = row.original;
      const canEdit =
        permissions.includes("CanEdit") || permissions.includes("CanAdmin");
      return (
        <AddConcept
          rowId={id}
          tableId={tableId}
          contentType="scanreportvalue"
          disabled={!canEdit}
          addSR={addSR}
        />
      );
    }
  }
];

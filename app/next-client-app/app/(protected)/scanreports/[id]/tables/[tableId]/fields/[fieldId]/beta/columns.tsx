"use client";
import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { ConceptTagsV3 } from "@/components/concepts/ConceptTagsV3";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import CopyButton from "@/components/core/CopyButton";
import AddConceptV3 from "@/components/concepts/AddConceptV3";

export const columns = (
  tableId: string,
  canEdit: boolean,
): ColumnDef<ScanReportValueV3>[] => [
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
    },
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
    enableSorting: false,
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
    enableSorting: false,
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
          <ConceptTagsV3
            concepts={concepts}
            scanReportId={"11"}
            tableId={tableId}
            fieldId={row.scan_report_field}
          />
        </Suspense>
      );
    },
  },
  {
    id: "Add Concept",
    header: "",
    cell: ({ row }) => {
      const { id } = row.original;

      return (
        <AddConceptV3
          rowId={id}
          tableId={tableId}
          contentType="scanreportvalue"
          disabled={!canEdit}
          scanReportId={"11"}
          fieldId={row.scan_report_field}
        />
      );
    },
  },
];

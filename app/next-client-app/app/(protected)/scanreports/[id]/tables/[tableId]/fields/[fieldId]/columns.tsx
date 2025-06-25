"use client";
import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { ConceptTags } from "@/components/concepts/concept-tags";
import AddConcept from "@/components/concepts/add-concept";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import CopyButton from "@/components/core/CopyButton";
import { AISuggestionsButton } from "@/components/recommendations/ai-suggesions-button";
import { Tooltips } from "@/components/core/Tooltips";
import { enable_ai_recommendation } from "@/constants";

// All Standard Columns
export const columns = (
  addSR: (concept: ScanReportConcept, c: Concept) => void,
  deleteSR: (id: number) => void,
  tableId: string
): ColumnDef<ScanReportValue>[] => {
  const baseColumns: ColumnDef<ScanReportValue>[] = [
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
            <a
              className="font-bold underline underline-offset-2"
              href={`https://athena.ohdsi.org/search-terms/terms?query=${value}`}
              target="_blank"
            >
              {value}
            </a>
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
            <ConceptTags concepts={concepts ?? []} deleteSR={deleteSR} />
          </Suspense>
        );
      },
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
      },
    },
  ];

  // AI Suggestions Column & setting as 4th Column
  if (enable_ai_recommendation === "true") {
    baseColumns.splice(3, 0, {
      id: "AI Suggestions",
      header: ({ column }) => (
        <div className="flex items-center">
          <DataTableColumnHeader column={column} title="AI Suggestions" />
          <Tooltips content="Get AI-powered Standard Concept Suggestions for the value. To get the better results, please select the most relevant domain." />
        </div>
      ),
      enableHiding: true,
      enableSorting: false,
      cell: ({ row }) => {
        const { value, id } = row.original;
        return (
          <AISuggestionsButton
            value={value}
            tableId={tableId}
            rowId={id}
            contentType="scanreportvalue"
          />
        );
      },
    });
  }

  return baseColumns;
};

"use client";
import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { ConceptTagsV3 } from "@/components/concepts/ConceptTagsV3";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import CopyButton from "@/components/core/CopyButton";
import AddConceptV3 from "@/components/concepts/AddConceptV3";
import { AISuggestionsButton } from "@/components/recommendations/ai-suggesions-button";
import { StoredRecommendationsButton } from "@/components/recommendations/stored-recommendations-button";
import { enableAIRecommendation, enableStoredRecommendation } from "@/constants";

export const columns = (
  tableId: string,
  canEdit: boolean,
  scanReportId: string
): ColumnDef<ScanReportValueV3>[] => [
  {
    id: "Value",
    accessorKey: "value",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Value" sortName="value" />
    ),
    enableHiding: true,
    enableSorting: true,
    cell: ({ row }) => {
      const { value, id } = row.original;

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
    }
  },
  {
    id: "Stored Recommendations",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Stored Recommendations" />
    ),
    enableHiding: true,
    enableSorting: false,
    cell: ({ row }) => {
      const { value, id, mapping_recommendations } = row.original;

      return (
        enableStoredRecommendation === "true" && (
        <div className="flex justify-start w-full">
          <StoredRecommendationsButton
            value={value}
            tableId={tableId}
            rowId={id}
            contentType="scanreportvalue"
            scanReportId={scanReportId}
            fieldId={row.original.scan_report_field}
              mappingRecommendations={mapping_recommendations}
            />
          </div>
        )
      );
    }
  },
  {
    id: "AI Suggestions",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="AI Suggestions" />
    ),
    enableHiding: true,
    enableSorting: false,
    cell: ({ row }) => {
      const { value, id } = row.original;

      return (
        <div className="flex justify-start w-full">
          {enableAIRecommendation === "true" ? (
            <AISuggestionsButton
              value={value}
              tableId={tableId}
              rowId={id}
              contentType="scanreportvalue"
            />
          ) : (
            <span className="text-gray-400 text-sm">Disabled</span>
          )}
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
    enableSorting: true,
    cell: ({ row }) => {
      const { value_description } = row.original;
      return (
        <span className="max-w-[200px] whitespace-pre-wrap text-pretty">
          {value_description}
        </span>
      );
    }
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
    enableSorting: true,
    cell: ({ row }) => {
      const { frequency } = row.original;
      return <span className="tabular-nums">{frequency}</span>;
    }
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
            scanReportId={scanReportId}
            tableId={tableId}
            fieldId={row.original.scan_report_field}
            valueId={row.original.id}
          />
        </Suspense>
      );
    }
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
          scanReportId={scanReportId}
          fieldId={row.original.scan_report_field}
        />
      );
    }
  }
];

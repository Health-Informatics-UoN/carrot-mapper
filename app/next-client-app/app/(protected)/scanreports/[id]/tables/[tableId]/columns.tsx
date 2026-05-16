"use client";

import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { EditButton } from "@/components/scanreports/EditButton";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import CopyButton from "@/components/core/CopyButton";
import { enableAIRecommendation } from "@/constants";
import { Tooltips } from "@/components/core/Tooltips";
import { AISuggestionsButton } from "@/components/recommendations/ai-suggesions-button";
import { ConceptTagsV3 } from "@/components/concepts/ConceptTagsV3";
import AddConceptV3 from "@/components/concepts/AddConceptV3";

export const columns = (
  tableId: string,
  canEdit: boolean,
  scanReportId: string,
): ColumnDef<ScanReportFieldV3>[] => {
  const baseColumns: ColumnDef<ScanReportFieldV3>[] = [
    {
      id: "Name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Field" sortName="name" />
      ),
      enableHiding: true,
      enableSorting: true,
      cell: ({ row }) => {
        const { id, name } = row.original;
        const prePath = usePathname();
        return (
          <div className="flex items-center gap-2">
            <Link
              href={`${
                prePath.endsWith("/") ? prePath : prePath + "/"
              }fields/${id}`}
            >
              <Button variant="link" className="font-bold">
                {name}
              </Button>
            </Link>
            <CopyButton textToCopy={name} />
          </div>
        );
      },
    },
    {
      id: "description",
      accessorKey: "description_column",
      header: ({ column }) => (
        <DataTableColumnHeader
          column={column}
          title="Description"
          sortName="description_column"
        />
      ),
      enableHiding: true,
      enableSorting: true,
      cell: ({ row }) => {
        const { description_column } = row.original;
        return (
          <span className="text-gray-500 max-w-[200px] whitespace-pre-wrap text-pretty">
            {description_column}
          </span>
        );
      },
    },
    {
      id: "Data Type",
      accessorKey: "type_column",
      header: ({ column }) => (
        <DataTableColumnHeader
          column={column}
          title="Data Type"
          sortName="type_column"
        />
      ),
      enableHiding: true,
      enableSorting: true,
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
          // Just in case the concepts tags need more time to load some data
          // --> showing skeleton having same width with the concept tag area
          <Suspense fallback={<Skeleton className="h-5 w-[250px]" />}>
            <ConceptTagsV3
              concepts={concepts ?? []}
              scanReportId={scanReportId}
              tableId={tableId}
              fieldId={row.original.id}
              valueId={0}
            />
          </Suspense>
        );
      },
    },
    {
      id: "Add Concept",
      header: "",
      cell: ({ row }) => {
        // const { scan_report_table, id, permissions } = row.original;
        // const canEdit =
        //   permissions.includes("CanEdit") || permissions.includes("CanAdmin");
        return (
          <AddConceptV3
            rowId={row.original.id}
            tableId={tableId}
            contentType="scanreportfield"
            disabled={false}
            scanReportId={scanReportId}
            fieldId={row.original.id}
          />
        );
      },
    },
  ];

  // AI Suggestions Column & setting as 4th Column
  if (enableAIRecommendation === "true") {
    baseColumns.splice(3, 0, {
      id: "AI Suggestions",
      header: ({ column }) => (
        <div className="flex items-center">
          <DataTableColumnHeader column={column} title="AI Suggestions" />
          <Tooltips content="Get AI-powered Standard Concept Suggestions for the field name. To get the better results, please select the most relevant domain." />
        </div>
      ),
      enableHiding: true,
      enableSorting: false,
      cell: ({ row }) => {
        const { name, id, scan_report_table } = row.original;
        return (
          <AISuggestionsButton
            value={name}
            tableId={tableId}
            rowId={id}
            contentType="scanreportfield"
          />
        );
      },
    });
  } else {
    baseColumns.splice(5, 0, {
      id: "edit",
      header: "",
      cell: ({ row }) => {
        const { id } = row.original;
        const path = usePathname();

        return (
          <EditButton
            prePath={path}
            fieldID={id}
            type="field"
            permissions={canEdit ? ["CanEdit"] : []}
          />
        );
      },
    });
  }
  return baseColumns;
};

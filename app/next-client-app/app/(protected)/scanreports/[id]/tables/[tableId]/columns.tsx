"use client";

import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { ConceptTags } from "@/components/concepts/concept-tags";
import AddConcept from "@/components/concepts/add-concept";
import { EditButton } from "@/components/scanreports/EditButton";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import CopyButton from "@/components/core/CopyButton";
import { enable_ai_recommendation } from "@/constants";
import { Tooltips } from "@/components/core/Tooltips";
import { AISuggestionsButton } from "@/components/recommendations/ai-suggesions-button";

export const columns = (
  addSR: (concept: ScanReportConcept, c: Concept) => void,
  deleteSR: (id: number) => void
): ColumnDef<ScanReportField>[] => {
  const baseColumns: ColumnDef<ScanReportField>[] = [
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
            <ConceptTags concepts={concepts ?? []} deleteSR={deleteSR} />
          </Suspense>
        );
      },
    },
    {
      id: "Add Concept",
      header: "",
      cell: ({ row }) => {
        const { scan_report_table, id, permissions } = row.original;
        const canEdit =
          permissions.includes("CanEdit") || permissions.includes("CanAdmin");
        return (
          <AddConcept
            rowId={id}
            tableId={scan_report_table.toString()}
            contentType="scanreportfield"
            disabled={canEdit ? false : true}
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
            tableId={scan_report_table.toString()}
            rowId={id}
          />
        );
      },
    });
  } else {
    baseColumns.splice(5, 0, {
      id: "edit",
      header: "",
      cell: ({ row }) => {
        const { id, permissions } = row.original;
        const path = usePathname();

        return (
          <EditButton
            prePath={path}
            fieldID={id}
            type="field"
            permissions={permissions}
          />
        );
      },
    });
  }
  return baseColumns;
};

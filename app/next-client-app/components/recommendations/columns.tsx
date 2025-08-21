"use client";

import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { Button } from "../ui/button";
import { Tooltips } from "../core/Tooltips";

export const columns = (
  tableId: string,
  rowId: number,
  onApplySuggestion: (data: {
    concept: number;
    object_id: number;
    content_type: string;
    creation_type: string;
    table_id: string;
  }) => void,
  contentType: string
): ColumnDef<UnisonConceptItem>[] => [
  {
    id: "Concept Name",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Concept Name" />
    ),
    cell: ({ row }) => {
      const { conceptName } = row.original;
      return <div className="w-[500px]">{conceptName}</div>;
    },
    enableSorting: false,
    enableHiding: true,
  },
  {
    id: "Concept ID",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Concept ID" />
    ),
    accessorKey: "conceptId",
    cell: ({ row }) => {
      const { conceptId } = row.original;
      return (
        <a
          className="text-blue-500 underline"
          target="_blank"
          href={`https://athena.ohdsi.org/search-terms/terms/${conceptId}`}
        >
          {conceptId}
        </a>
      );
    },
    enableSorting: false,
    enableHiding: true,
  },
  {
    id: "Vocabulary",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Vocabulary" />
    ),
    enableSorting: false,
    enableHiding: true,
    accessorKey: "vocabulary",
  },
  {
    id: "Accuracy",
    header: ({ column }) => (
      <div className="text-center w-full">
        <DataTableColumnHeader column={column} title="Accuracy/Confidence" />
      </div>
    ),
    enableSorting: false,
    enableHiding: true,
    cell: ({ row }) => {
      const { accuracy, explanation } = row.original;
      return (
        <div className="text-center w-full flex items-center justify-center gap-1">
          {accuracy}
          <Tooltips
            content={`Explanation: ${
              accuracy === 100 ? "Exact Match" : explanation
            }`}
            side="bottom"
          />
        </div>
      );
    },
  },
  {
    id: "Action",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Action" />
    ),
    cell: ({ row }) => {
      const { conceptId } = row.original;
      return (
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            onApplySuggestion({
              concept: conceptId,
              object_id: rowId,
              content_type: contentType,
              creation_type: "M",
              table_id: tableId,
            });
          }}
        >
          Add
        </Button>
      );
    },
    enableSorting: false,
    enableHiding: true,
  },
];

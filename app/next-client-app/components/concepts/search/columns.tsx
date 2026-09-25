"use client";

import { Badge } from "@/components/ui/badge";
import { ColumnDef } from "@tanstack/react-table";
import { ConceptSearchDetailsSheet } from "./ConceptSearchDetailsSheet";

export const columns: ColumnDef<ConceptSearchResult>[] = [
  {
    id: "Concept ID",
    accessorKey: "concept_id",
    header: "Concept ID",
  },
  {
    id: "Name",
    accessorKey: "concept_name",
    header: "Name",
    cell: ({ row }) => (
      <ConceptSearchDetailsSheet concept={row.original}>
        <button className="text-left hover:underline">
          {row.original.concept_name}
        </button>
      </ConceptSearchDetailsSheet>
    ),
  },
  {
    id: "Code",
    accessorKey: "concept_code",
    header: "Code",
  },
  {
    id: "Domain",
    accessorKey: "domain_id",
    header: "Domain",
  },
  {
    id: "Vocabulary",
    accessorKey: "vocabulary_id",
    header: "Vocabulary",
  },
  {
    id: "Class",
    accessorKey: "concept_class_id",
    header: "Class",
  },
  {
    id: "Standard",
    accessorKey: "standard_concept",
    header: "Standard",
    cell: ({ row }) =>
      row.original.standard_concept === "S" ? (
        <Badge variant="secondary">Standard</Badge>
      ) : null,
  },
];

"use client";

import * as React from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { DataTable } from "../data-table";
import { UnisonConceptItem } from "@/types/recommendation";
import { columns } from "./columns";
import { recommendationServiceName } from "@/constants";
import { InfoItem } from "../core/InfoItem";

interface AISuggestionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  suggestions: UnisonConceptItem[];
  onApplySuggestion: (data: {
    concept: number;
    object_id: number;
    content_type: string;
    creation_type: string;
    table_id: string;
  }) => void;
  searchedValue: string;
  tableId: string;
  rowId: number;
  domainId: string;
  contentType: string;
}

// Main dialog component combining all parts
export default function AISuggestionDialog({
  open,
  onOpenChange,
  suggestions,
  onApplySuggestion,
  searchedValue,
  tableId,
  rowId,
  domainId,
  contentType,
}: AISuggestionDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-screen-xl overflow-auto max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="text-xl text-center">
            AI Mapping Suggestions
          </DialogTitle>

          <div className="flex flex-col md:flex-row md:items-center h-7 justify-center space-y-2 md:space-y-0 divide-y md:divide-y-0 md:divide-x divide-gray-300">
            <InfoItem
              label="Value queried"
              value={searchedValue}
              className="py-1 md:py-0 md:pr-3"
            />
            <InfoItem
              label="Domain Chosen"
              value={domainId}
              className="py-1 md:py-0 md:px-3"
            />
            <InfoItem
              label="Recommendation AI Model"
              value={
                recommendationServiceName
                  ? recommendationServiceName.charAt(0).toUpperCase() +
                    recommendationServiceName.slice(1)
                  : "Unknown AI Model"
              }
              className="py-1 md:py-0 md:px-3"
            />
          </div>
        </DialogHeader>

        {suggestions.length > 0 ? (
          <DataTable
            columns={columns(tableId, rowId, onApplySuggestion, contentType)}
            data={suggestions}
            count={suggestions.length}
            paginated={false}
            viewColumns={false}
            overflow={false}
          />
        ) : (
          "No suggestions found"
        )}
      </DialogContent>
    </Dialog>
  );
}

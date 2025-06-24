"use client";

import * as React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../ui/dialog";
import { DataTable } from "../data-table";
import { UnisonConceptItem } from "@/types/recommendation";
import { columns } from "./columns";
import { recommendation_service_name } from "@/constants";

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
}

// Main dialog component combining all parts
const AISuggestionDialog = React.forwardRef<
  HTMLDivElement,
  AISuggestionDialogProps
>(
  (
    {
      open,
      onOpenChange,
      suggestions,
      onApplySuggestion,
      searchedValue,
      tableId,
      rowId,
    },
    ref
  ) => (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent ref={ref} className="max-w-screen-xl overflow-auto h-1/2">
        <DialogHeader>
          <DialogTitle className="text-lg">
            AI Mapping Suggestions 🥕
          </DialogTitle>
          <DialogDescription>
            <div className="mb-2">
              <span className="font-semibold">Value:</span> {searchedValue}
            </div>
            {suggestions.length > 0 && recommendation_service_name ? (
              <>
                <span className="font-semibold">Recommendation AI Model:</span>{" "}
                {recommendation_service_name.charAt(0).toUpperCase() +
                  recommendation_service_name.slice(1)}{" "}
                |<span className="font-semibold ml-2">Metrics Used:</span>{" "}
                Semantic Similarity
              </>
            ) : (
              "Loading recommendation details..."
            )}
          </DialogDescription>
        </DialogHeader>

        {suggestions.length > 0 ? (
          <DataTable
            columns={columns(tableId, rowId, onApplySuggestion)}
            data={suggestions}
            count={suggestions.length}
            paginated={false}
            viewColumns={false}
            overflow={false}
          />
        ) : (
          "Retrieving Jobs"
        )}
      </DialogContent>
    </Dialog>
  )
);
AISuggestionDialog.displayName = "AISuggestionDialog";

export { AISuggestionDialog };

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
  isLoading: boolean;
  suggestions: UnisonConceptItem[];
  fetchError: string | null;
  onApplySuggestion: (suggestion: UnisonConceptItem) => void;
  searchedValue: string;
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
      isLoading,
      suggestions,
      fetchError,
      onApplySuggestion,
      searchedValue,
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
                Accuracy
              </>
            ) : (
              "Loading recommendation details..."
            )}
          </DialogDescription>
        </DialogHeader>

        {suggestions.length > 0 ? (
          <DataTable
            columns={columns}
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

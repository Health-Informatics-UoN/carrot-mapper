"use client";

import * as React from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { DataTable } from "../data-table";
import { columns } from "./columns";
import { InfoItem } from "../core/InfoItem";

interface RecommendationsDialogProps {
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
  source: "unison" | "v3";
}

// Shared dialog component for both Unison and V3 recommendations
export default function RecommendationsDialog({
  open,
  onOpenChange,
  suggestions,
  onApplySuggestion,
  searchedValue,
  tableId,
  rowId,
  domainId,
  contentType,
  source
}: RecommendationsDialogProps) {
  const getSourceLabel = () => {
    return source === "v3"
      ? "Stored Mapping Recommendations"
      : "Live Mapping Recommendations";
  };

  const getSourceDescription = () => {
    return source === "v3"
      ? "Pre-computed mapping recommendations from the database"
      : "Mapping recommendations";
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-screen-xl overflow-auto max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="text-xl text-center">
            {getSourceLabel()}
          </DialogTitle>

          <div className="flex flex-col md:flex-row md:items-center h-7 justify-center space-y-2 md:space-y-0 divide-y md:divide-y-0 md:divide-x divide-gray-300">
            <InfoItem
              label="Value queried"
              value={searchedValue}
              className="py-1 md:py-0 md:pr-3"
            />
            {source === "unison" && (
              <InfoItem
                label="Domain Chosen"
                value={domainId}
                className="py-1 md:py-0 md:px-3"
              />
            )}
            <InfoItem
              label="Source"
              value={getSourceDescription()}
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
          <div className="text-center py-8 text-gray-500">
            No recommendations found
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

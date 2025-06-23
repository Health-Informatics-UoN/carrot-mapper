"use client";

import * as React from "react";
import { Button } from "./button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "./dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./table";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

// - Reuse it from types

// Interface matching the API response structure
export interface AISuggestion {
  conceptCode: string;     // Code of the recommended concept
  conceptName: string;     // Name of the recommended concept
  matchScore: number;      // Score indicating how good the match is (0-1)
  recommendedBy: string;   // System or algorithm that made the recommendation
  metricsUsed: string;     // Metrics used for the recommendation
}

// - Move to types

// Props interface for the main dialog component
interface AISuggestionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isLoading: boolean;
  suggestions: AISuggestion[];
  fetchError: string | null;
  onApplySuggestion: (suggestion: AISuggestion) => void;
  searchedValue: string;
}

// Table component that displays the suggestions in a structured format
const AISuggestionTable = React.forwardRef<
  HTMLTableElement,
  {
    suggestions: AISuggestion[];
    onApplySuggestion: (suggestion: AISuggestion) => void;
  }
>(({ suggestions, onApplySuggestion }, ref) => (
  <Table ref={ref}>
    {/* Table header defining columns */}
    <TableHeader>
      <TableRow>
        <TableHead>Concept Name</TableHead>
        <TableHead>Code</TableHead>
        <TableHead>Match Score</TableHead>
        <TableHead>Action</TableHead>
      </TableRow>
    </TableHeader>
    {/* Table body mapping through suggestions */}
    <TableBody>
      {suggestions.map((suggestion, index) => (
        <TableRow key={`${suggestion.conceptCode}-${index}`}>
          <TableCell className="font-medium">
            {suggestion.conceptName}
          </TableCell>
          <TableCell>{suggestion.conceptCode}</TableCell>
          <TableCell>{suggestion.matchScore}%</TableCell>
          <TableCell>
            <Button size="sm" onClick={() => onApplySuggestion(suggestion)}>
              Apply
            </Button>
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
));
AISuggestionTable.displayName = "AISuggestionTable";

// Main content component handling different states (loading, error, data display)
const AISuggestionContent = React.forwardRef<
  HTMLDivElement,
  {
    isLoading: boolean;
    fetchError: string | null;
    suggestions: AISuggestion[];
    onApplySuggestion: (suggestion: AISuggestion) => void;
  }
>(({ isLoading, fetchError, suggestions, onApplySuggestion }, ref) => (
  <div ref={ref} className="max-h-[400px] overflow-y-auto py-4">
    {fetchError ? (
      <div className="text-red-500 text-center py-4">{fetchError}</div>
    ) : isLoading ? (
      <div className="flex items-center justify-center py-4">
        <Loader2 className="h-6 w-6 animate-spin" />
        <span className="ml-2">Loading suggestions...</span>
      </div>
    ) : suggestions.length > 0 ? (
      <AISuggestionTable
        suggestions={suggestions}
        onApplySuggestion={onApplySuggestion}
      />
    ) : (
      <p className="text-center text-muted-foreground py-4">
        No suggestions available
      </p>
    )}
  </div>
));
AISuggestionContent.displayName = "AISuggestionContent";

// Footer component with close button
const AISuggestionFooter = React.forwardRef<
  HTMLDivElement,
  { onClose: () => void } & React.HTMLAttributes<HTMLDivElement>
>(({ onClose, className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center justify-end gap-2 pt-4", className)}
    {...props}
  >
    <Button
      variant="outline"
      size="sm"
      onClick={onClose}
      className="border-red-500 text-red-500 hover:bg-red-50 hover:text-red-600"
    >
      Close
    </Button>
  </div>
));
AISuggestionFooter.displayName = "AISuggestionFooter";

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
      searchedValue
    },
    ref
  ) => (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent ref={ref} className="sm:max-w-[700px]">
        <DialogHeader>
          <DialogTitle className="text-lg">AI Mapping Suggestions 🥕</DialogTitle>
          <DialogDescription>
            <div className="mb-2">
              <span className="font-semibold">Previous Value Code :</span> {searchedValue}
            </div>
            {suggestions.length > 0 ? (
              <>
                <span className="font-semibold">Recommendation AI Model:</span> {suggestions[0].recommendedBy} | 
                <span className="font-semibold ml-2">Metrics Used:</span> {suggestions[0].metricsUsed}
              </>
            ) : (
              "Loading recommendation details..."
            )}
          </DialogDescription>
        </DialogHeader>

        <AISuggestionContent
          isLoading={isLoading}
          fetchError={fetchError}
          suggestions={suggestions}
          onApplySuggestion={onApplySuggestion}
        />

        <AISuggestionFooter onClose={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  )
);
AISuggestionDialog.displayName = "AISuggestionDialog";

export { AISuggestionDialog };
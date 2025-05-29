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

// Interface defining the structure of an AI suggestion

export interface AISuggestion {
  id: string;
  conceptName: string;
  conceptCode: string;
  matchScore: number;
  source: string;
  recommendationBy: string;
  metricsUsed: string;
}

// Props interface for the main dialog component

interface AISuggestionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isLoading: boolean;
  suggestions: AISuggestion[];
  fetchError: string | null;
  onApplySuggestion: (suggestion: AISuggestion) => void;
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
        <TableHead>Source</TableHead>
        <TableHead>Action</TableHead>
      </TableRow>
    </TableHeader>
    {/* Table body mapping through suggestions */}
    <TableBody>
      {suggestions.map((suggestion) => (
        <TableRow key={suggestion.id}>
          <TableCell className="font-medium">
            {suggestion.conceptName}
          </TableCell>
          <TableCell>{suggestion.conceptCode}</TableCell>
          <TableCell>{Math.round(suggestion.matchScore * 100)}%</TableCell>
          <TableCell>{suggestion.source}</TableCell>
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
    },
    ref
  ) => (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent ref={ref} className="sm:max-w-[700px]">
        <DialogHeader>
          <DialogTitle>AI Mapping Suggestions</DialogTitle>
          <DialogDescription>
            {suggestions.length > 0 ? (
              <>
                Recommendation AI Model: {suggestions[0].recommendationBy} |
                Metrics Used: {suggestions[0].metricsUsed}
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

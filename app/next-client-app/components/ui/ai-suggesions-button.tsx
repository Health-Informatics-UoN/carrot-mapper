"use client";
import { useState } from "react";
import { Button } from "./button";
import { Tooltip, TooltipContent, TooltipTrigger } from "./tooltip";
import { Sparkles, Loader2 } from "lucide-react";
import { AISuggestionDialog } from "./ai-suggestions-dialog";
import type { AISuggestion } from "./ai-suggestions-dialog";

/**
   * The AI suggestion selected by the user
    * - Tooltip
    * - Button to trigger API call for AI Suggestion
    * - Dialog component to display AI suggestions
  */

export function AISuggestionsButton() {
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Fetches AI suggestions from the API

  const handleClick = async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      // API logic will be added here later

      // Undo Comments for testing the Button Get AI Suggestions in the UI

      {
        /* Testing Logic Starts*/
      }

      // const mockSuggestions: AISuggestion[] = [
      //   {
      //     id: "1",
      //     conceptName: "Diabetes Mellitus",
      //     conceptCode: "44054006",
      //     matchScore: 0.92,
      //     source: "SNOMED CT",
      //     recommendationBy: "Lettuce",
      //     metricsUsed: "Semantic Similarity",
      //   },
      //   {
      //     id: "2",
      //     conceptName: "Type 2 Diabetes",
      //     conceptCode: "44054006-2",
      //     matchScore: 0.85,
      //     source: "SNOMED CT",
      //     recommendationBy: "Lettuce",
      //     metricsUsed: "Semantic Similarity",
      //   },
      //   {
      //     id: "3",
      //     conceptName: "Hypertension",
      //     conceptCode: "38341003",
      //     matchScore: 0.78,
      //     source: "ICD-10",
      //     recommendationBy: "Lettuce",
      //     metricsUsed: "Semantic Similarity",
      //   },
      //   {
      //     id: "4",
      //     conceptName: "Myocardial Infarction",
      //     conceptCode: "22298006",
      //     matchScore: 0.73,
      //     source: "ICD-40",
      //     recommendationBy: "Lettuce",
      //     metricsUsed: "Semantic Similarity",
      //   },
      //   {
      //     id: "5",
      //     conceptName: "Chronic Kidney Disease",
      //     conceptCode: "709044004",
      //     matchScore: 0.69,
      //     source: "LOINC",
      //     recommendationBy: "Lettuce",
      //     metricsUsed: "Semantic Similarity",
      //   },
      // ];

      // await new Promise((resolve) => setTimeout(resolve, 1000));
      // setSuggestions(mockSuggestions);

      {
        /* Testing Logic Ends*/
      }

      setIsOpen(true);
    } catch (error) {
      setFetchError("Failed to fetch suggestions. Please try again.");
      console.error("Error fetching suggestions:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Button & Tooltip functionality

  const handleApplySuggestion = (suggestion: AISuggestion) => {
    console.log("Applying suggestion:", suggestion);
    setIsOpen(false);
  };

  return (
    <>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="outline"
            className="gap-2 border-purple-400 hover:bg-purple-100 hover:text-black"
            onClick={handleClick}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4 text-purple-500" />
            )}
            Get AI Suggestions
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>Get AI-powered mapping suggestions</p>
        </TooltipContent>
      </Tooltip>

      <AISuggestionDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        isLoading={isLoading}
        suggestions={suggestions}
        fetchError={fetchError}
        onApplySuggestion={handleApplySuggestion}
      />
    </>
  );
}

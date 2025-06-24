"use client";
import { useState } from "react";
import { Button } from "../ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "../ui/tooltip";
import { Sparkles, Loader2 } from "lucide-react";
import { AISuggestionDialog } from "./ai-suggestions-dialog";
import { getConceptRecommendationsUnison } from "@/api/recommendations";
import { UnisonConceptItem } from "@/types/recommendation";
import { addConcept } from "@/api/concepts";
import { toast } from "sonner";

export function AISuggestionsButton({
  value,
  tableId,
  rowId,
}: {
  value: string;
  tableId: string;
  rowId: number;
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<UnisonConceptItem[]>([]);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Fetches AI suggestions from the API
  const handleClick = async () => {
    if (!value) {
      setFetchError("No value provided to search for recommendations");
      return;
    }

    setIsLoading(true);
    setFetchError(null);

    try {
      // Call the getConceptRecommendations function
      const recommendations = await getConceptRecommendationsUnison(value);
      // Filter to get only unique concept IDs
      const uniqueRecommendations = recommendations.items.filter(
        (item, index, array) =>
          array.findIndex((i) => i.conceptId === item.conceptId) === index
      );

      setSuggestions(uniqueRecommendations);
      setIsOpen(true);
    } catch (error) {
      console.error("Error generating suggestions:", error);
      setFetchError("Failed to fetch suggestions. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleApplySuggestion = async (data: {
    concept: number;
    object_id: number;
    content_type: string;
    creation_type: string;
    table_id: string;
  }) => {
    setIsOpen(false);
    const response = await addConcept(data);
    if (response) {
      toast.error(`Adding concept failed. ${response.errorMessage}`);
    } else {
      toast.success(`OMOP Concept successfully added.`);
      // Reload the page after 500ms to avoid race condition
      setTimeout(() => {
        window.location.reload();
      }, 500);
    }
  };

  return (
    <>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="gap-2 border-purple-400 hover:bg-purple-100 hover:text-black"
            onClick={handleClick}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4 text-purple-500" />
            )}
            Use AI Assistant
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>Get AI-powered Concept Suggestions for "{value}"</p>
        </TooltipContent>
      </Tooltip>

      <AISuggestionDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        suggestions={suggestions}
        onApplySuggestion={handleApplySuggestion}
        searchedValue={value}
        tableId={tableId}
        rowId={rowId}
      />
    </>
  );
}

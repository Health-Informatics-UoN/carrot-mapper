"use client";
import { useState } from "react";
import { Button } from "../ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "../ui/tooltip";
import { Sparkles, Loader2 } from "lucide-react";
import { AISuggestionDialog } from "./ai-suggestions-dialog";
import { getConceptRecommendationsUnison } from "@/api/recommendations";
import { UnisonConceptItem } from "@/types/recommendation";

export function AISuggestionsButton({ value }: { value: string }) {
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

  const handleApplySuggestion = (suggestion: UnisonConceptItem) => {
    console.log("Applying suggestion:", suggestion);
    setIsOpen(false);
    // Here you would implement the logic to apply the concept
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
        isLoading={isLoading}
        suggestions={suggestions}
        fetchError={fetchError}
        onApplySuggestion={handleApplySuggestion}
        searchedValue={value}
      />
    </>
  );
}

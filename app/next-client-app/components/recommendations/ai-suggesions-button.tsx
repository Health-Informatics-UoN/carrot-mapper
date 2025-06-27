"use client";
import { useState } from "react";
import { Button } from "../ui/button";
import { Sparkles, Loader2 } from "lucide-react";
import AISuggestionDialog from "./ai-suggestions-dialog";
import { getConceptRecommendationsUnison } from "@/api/recommendations";
import { UnisonConceptItem } from "@/types/recommendation";
import { addConcept } from "@/api/concepts";
import { toast } from "sonner";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { domains } from "@/constants/domains";
import { DropdownMenuItem } from "@radix-ui/react-dropdown-menu";

export function AISuggestionsButton({
  value,
  tableId,
  rowId,
  contentType,
}: {
  value: string;
  tableId: string;
  rowId: number;
  contentType: string;
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<UnisonConceptItem[]>([]);
  const [domainId, setDomainId] = useState<string>("");

  // Fetches AI suggestions from the API
  const handleClick = async (domainId: string) => {
    if (!value) {
      toast.error("No value provided to search for recommendations");
      return;
    }

    setIsLoading(true);

    try {
      // Call the getConceptRecommendations function
      const recommendations = await getConceptRecommendationsUnison(
        value,
        domainId
      );
      // Filter to get only unique concept IDs
      const uniqueRecommendations = recommendations.items.filter(
        (item, index, array) =>
          array.findIndex((i) => i.conceptId === item.conceptId) === index
      );

      setSuggestions(uniqueRecommendations);
      setIsOpen(true);
    } catch (error) {
      console.error("Error generating suggestions:", error);
      toast.error("Failed to fetch suggestions. Please try again.");
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
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <div className="flex focus:outline-none">
            <Button
              variant="outline"
              size="sm"
              className="gap-2 border-purple-400 hover:bg-purple-100 hover:text-black"
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4 text-purple-500" />
              )}
              Get Suggestions
            </Button>
          </div>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="start"
          className="w-52 overflow-y-auto max-h-96"
        >
          <DropdownMenuLabel className="text-black font-semibold text-center">
            Select Relevant Domain
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {domains.map((domain) => {
            return (
              <DropdownMenuItem
                key={domain.id}
                className="cursor-pointer hover:bg-blue-100 hover:text-black focus:outline-none p-1"
                onClick={() => {
                  setDomainId(domain.id);
                  handleClick(domain.id);
                }}
              >
                {domain.id}
              </DropdownMenuItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      <AISuggestionDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        suggestions={suggestions}
        onApplySuggestion={handleApplySuggestion}
        searchedValue={value}
        tableId={tableId}
        rowId={rowId}
        domainId={domainId}
        contentType={contentType}
      />
    </>
  );
}

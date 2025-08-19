"use client";
import { useState } from "react";
import { Button } from "../ui/button";
import { Sparkles, Loader2 } from "lucide-react";
import AISuggestionDialog from "./ai-suggestions-dialog";
import { getConceptRecommendationsUnison } from "@/api/recommendations";
import { UnisonConceptItem } from "@/types/recommendation";
import { addConcept, getSuggestionsV3 } from "@/api/concepts";
import { toast } from "sonner";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { domains } from "@/constants/domains";
import { DropdownMenuItem } from "@radix-ui/react-dropdown-menu";

export function AISuggestionsButton({
  value,
  tableId,
  rowId,
  contentType,
  scanReportId,
  fieldId
}: {
  value: string;
  tableId: string;
  rowId: number;
  contentType: string;
  scanReportId?: string;
  fieldId?: number;
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
      const recommendations = await fetchRecommendations(domainId);
      const uniqueRecommendations = deduplicateRecommendations(
        recommendations.items
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

  // Fetch recommendations from appropriate source
  const fetchRecommendations = async (domainId: string) => {
    if (canUseV3Endpoint()) {
      // Use v3 endpoint to fetch from mapping_recommendations table
      return await fetchFromV3Endpoint();
    }

    // Fallback to Unison service when v3 endpoint not available
    return await fetchFromUnisonService(domainId);
  };

  // Check if we can use the v3 endpoint
  const canUseV3Endpoint = () => {
    return Boolean(scanReportId && fieldId);
  };

  // Fetch recommendations from v3 endpoint (mapping_recommendations table)
  const fetchFromV3Endpoint = async () => {
    const v3Response = await getSuggestionsV3(
      scanReportId!,
      tableId,
      fieldId!.toString()
    );

    const targetValue = v3Response.results.find(
      (result) => result.value === value
    );

    if (hasMappingRecommendations(targetValue)) {
      return {
        items: transformMappingRecommendations(
          targetValue!.mapping_recommendations
        )
      };
    }

    return {
      items: [],
      message:
        "V3 endpoint is available but no AI recommendations found for this value."
    };
  };

  // Check if target value has mapping recommendations
  const hasMappingRecommendations = (
    targetValue: ScanReportValueV3 | undefined
  ) => {
    return Boolean(targetValue?.mapping_recommendations?.length);
  };

  // Transform mapping recommendations to expected format
  const transformMappingRecommendations = (
    recommendations: MappingRecommendation[]
  ) => {
    return recommendations.map((rec) => ({
      accuracy: rec.score ?? null, // Keep as null, handle in UI
      conceptId: rec.concept.concept_id,
      conceptName: rec.concept.concept_name,
      conceptCode: rec.concept.concept_code,
      vocabulary: rec.concept.vocabulary_id ?? "Unknown",
      domain: rec.concept.domain_id ?? "Unknown",
      conceptClass: rec.concept.concept_class_id ?? "Unknown",
      explanation: rec.score
        ? `AI recommendation from ${rec.tool_name} (score: ${rec.score})`
        : `AI recommendation from ${rec.tool_name} (no score)`
    }));
  };

  // Fetch recommendations from Unison service (external API call)
  const fetchFromUnisonService = async (domainId: string) => {
    try {
      return await getConceptRecommendationsUnison(value, domainId);
    } catch (error) {
      console.error("Unison service failed:", error);
      return { items: [] };
    }
  };

  // Remove duplicate recommendations by concept ID
  const deduplicateRecommendations = (items: UnisonConceptItem[]) => {
    return items.filter(
      (item, index, array) =>
        array.findIndex((i) => i.conceptId === item.conceptId) === index
    );
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
          <div className="flex focus:outline-hidden">
            <Button
              variant="ghost"
              size="sm"
              className="border-purple-400 hover:bg-purple-100 hover:text-black dark:hover:bg-gray-700 dark:hover:text-white"
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4 text-purple-500" />
              )}
              Suggestions
            </Button>
          </div>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="start"
          className="w-52 overflow-y-auto max-h-96"
        >
          <DropdownMenuLabel className="text-black dark:text-white font-semibold text-center">
            Select Relevant Domain
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {domains.map((domain) => {
            return (
              <DropdownMenuItem
                key={domain.id}
                className="cursor-pointer hover:bg-blue-100 hover:text-black focus:outline-hidden p-1"
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

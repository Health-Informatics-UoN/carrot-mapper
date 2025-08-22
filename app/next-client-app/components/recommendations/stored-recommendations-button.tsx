"use client";
import { useState } from "react";
import { Button } from "../ui/button";
import { Sparkles } from "lucide-react";
import RecommendationsDialog from "./stored-recommendations-dialog";
import { addConcept } from "@/api/concepts";
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

export function StoredRecommendationsButton({
  value,
  tableId,
  rowId,
  contentType,
  mappingRecommendations
}: {
  value: string;
  tableId: string;
  rowId: number;
  contentType: string;
  scanReportId: string;
  fieldId: number;
  mappingRecommendations: MappingRecommendation[];
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<UnisonConceptItem[]>([]);
  const [domainId, setDomainId] = useState<string>("");

  // Handle click to show stored recommendations
  const handleClick = () => {
    if (!value) {
      toast.error("No value provided to search for recommendations");
      return;
    }

    if (!mappingRecommendations || mappingRecommendations.length === 0) {
      toast.info("No pre-computed recommendations found for this value");
      return;
    }

    // Transform the recommendations we already have
    const transformedRecommendations = transformMappingRecommendations(
      mappingRecommendations
    );
    setSuggestions(transformedRecommendations);
    setIsOpen(true);
  };

  // Transform mapping recommendations to expected format
  const transformMappingRecommendations = (
    recommendations: MappingRecommendation[]
  ): UnisonConceptItem[] => {
    return recommendations.map((rec) => ({
      accuracy: rec.score ?? null,
      conceptId: rec.concept.concept_id,
      conceptName: rec.concept.concept_name,
      conceptCode: rec.concept.concept_code,
      vocabulary: rec.concept.vocabulary_id ?? "Unknown",
      domain: rec.concept.domain_id ?? "Unknown",
      conceptClass: rec.concept.concept_class_id ?? "Unknown",
      explanation: rec.score
        ? `Pre-computed recommendation from ${rec.tool_name} (score: ${rec.score})`
        : `Pre-computed recommendation from ${rec.tool_name} (no score)`
    }));
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
              className={`border-purple-400 hover:bg-purple-100 hover:text-black dark:hover:bg-gray-700 dark:hover:text-white ${
                !mappingRecommendations || mappingRecommendations.length === 0
                  ? "opacity-50 cursor-not-allowed"
                  : ""
              }`}
              disabled={
                !mappingRecommendations || mappingRecommendations.length === 0
              }
            >
              <Sparkles className="h-4 w-4 text-purple-500" />
              {mappingRecommendations && mappingRecommendations.length > 0
                ? "Recommendations"
                : "No Recommendations"}
            </Button>
          </div>
        </DropdownMenuTrigger>
        {mappingRecommendations && mappingRecommendations.length > 0 && (
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
                    handleClick();
                  }}
                >
                  {domain.id}
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuContent>
        )}
      </DropdownMenu>

      <RecommendationsDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        suggestions={suggestions}
        onApplySuggestion={handleApplySuggestion}
        searchedValue={value}
        tableId={tableId}
        rowId={rowId}
        domainId={domainId}
        contentType={contentType}
        source="v3"
      />
    </>
  );
}

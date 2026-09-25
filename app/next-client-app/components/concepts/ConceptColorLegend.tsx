import { InfoIcon } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { CONCEPT_CREATION_TYPES } from "@/constants";

// Must match the chip colours rendered in ConceptTagsV3.tsx exactly.
const SWATCH_CLASSES: Record<keyof typeof CONCEPT_CREATION_TYPES, string> = {
  V: "bg-rose-200",
  M: "bg-blue-200",
  R: "bg-emerald-200",
  X: "bg-amber-200",
};

export function ConceptColorLegend() {
  return (
    <TooltipProvider delayDuration={100}>
      <Tooltip>
        <TooltipTrigger asChild>
          <InfoIcon className="ml-1 h-4 w-4 shrink-0 text-muted-foreground cursor-help" />
        </TooltipTrigger>
        <TooltipContent
          side="top"
          align="start"
          className="w-72 max-w-72 whitespace-normal text-left"
        >
          <p className="mb-2 font-semibold">How concepts are matched</p>
          <div className="space-y-1.5">
            {(
              Object.keys(CONCEPT_CREATION_TYPES) as Array<
                keyof typeof CONCEPT_CREATION_TYPES
              >
            ).map((key) => {
              const type = CONCEPT_CREATION_TYPES[key];
              return (
                <div key={key} className="flex items-start gap-2">
                  <span
                    className={`mt-1 h-3 w-3 shrink-0 rounded-sm border border-black/10 ${SWATCH_CLASSES[key]}`}
                  />
                  <span className="min-w-0 flex-1 break-words">
                    <span className="font-medium">{type.label}</span>
                    <span className="text-muted-foreground">
                      {" "}
                      &mdash; {type.description}
                    </span>
                  </span>
                </div>
              );
            })}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

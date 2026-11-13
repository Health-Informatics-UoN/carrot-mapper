"use client";

import { Info, TriangleAlert } from "lucide-react";
import { Portal as TooltipPortal } from "@radix-ui/react-tooltip";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface Props {
  includeAuthorOrcidIds: boolean;
  onIncludeChange: (include: boolean) => void;
}

export function RegistryOrcidFields({
  includeAuthorOrcidIds,
  onIncludeChange,
}: Props) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Checkbox
          id="include-orcids"
          name="include_author_orcid_ids"
          checked={includeAuthorOrcidIds}
          onCheckedChange={(checked) => onIncludeChange(checked === true)}
        />
        <Label htmlFor="include-orcids">Include ORCID(s)</Label>
        <TooltipProvider delayDuration={100}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" aria-label="ORCID information" className="ml-1 text-muted-foreground">
                <Info className="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipPortal>
              <TooltipContent collisionPadding={8} className="max-w-[min(24rem,calc(100vw-2rem))] text-center whitespace-pre-wrap">
                Include author and co-author ORCID identifiers from their profiles in the SSSOM metadata.
              </TooltipContent>
            </TooltipPortal>
          </Tooltip>
        </TooltipProvider>
      </div>
      {includeAuthorOrcidIds && (
        <div className="ml-3 flex items-center gap-3 border-l-2 border-border bg-muted/30 px-3 py-2 text-sm text-foreground">
          <TriangleAlert aria-hidden="true" className="size-5 shrink-0 text-muted-foreground" />
          <p>Please make sure your ORCID and co-authors&apos; ORCIDs are added in the My profile page. Missing ORCIDs won&apos;t show in the published SSSOM.</p>
        </div>
      )}
    </div>
  );
}
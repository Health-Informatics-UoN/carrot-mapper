"use client";

import { useRef } from "react";
import { Info, Plus, Trash2 } from "lucide-react";
import { Portal as TooltipPortal } from "@radix-ui/react-tooltip";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export type OrcidEntry = { key: number; value: string };

interface Props {
  includeOrcids: boolean;
  orcids: OrcidEntry[];
  onIncludeChange: (include: boolean) => void;
  onOrcidsChange: (orcids: OrcidEntry[]) => void;
}

export function RegistryOrcidFields({
  includeOrcids,
  orcids,
  onIncludeChange,
  onOrcidsChange,
}: Props) {
  const nextOrcidKey = useRef(1);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Checkbox
          id="include-orcids"
          checked={includeOrcids}
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
                Add author and co-author ORCID identifiers to the SSSOM metadata.
              </TooltipContent>
            </TooltipPortal>
          </Tooltip>
        </TooltipProvider>
      </div>
      {includeOrcids && (
        <div className="ml-6 space-y-3">
          <div className="flex items-start gap-2 rounded-md bg-muted/60 p-3 text-xs text-muted-foreground">
            <Info className="mt-0.5 size-4 shrink-0" />
            <span>Enter your ORCID and any co-authors&apos; ORCIDs below. Missing ORCIDs will not appear in the published SSSOM.</span>
          </div>
          {orcids.map((item, index) => (
              <div className="space-y-1" key={item.key}>
                <div className="flex items-center justify-between">
                  <Label htmlFor={`orcid-${item.key}`}>ORCID {index + 1}</Label>
                  {orcids.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => onOrcidsChange(orcids.filter((entry) => entry.key !== item.key))}
                      aria-label={`Remove ORCID ${index + 1}`}
                    >
                      <Trash2 className="size-4" /> Remove
                    </Button>
                  )}
                </div>
                <Input
                  id={`orcid-${item.key}`}
                  value={item.value}
                  onChange={(event) => {
                    const value = event.target.value;
                    onOrcidsChange(orcids.map((entry) => entry.key === item.key ? { ...entry, value } : entry));
                  }}
                  placeholder="0000-0002-1825-0097"
                />
              </div>
          ))}
          <Button type="button" size="sm" variant="outline" onClick={() => onOrcidsChange([...orcids, { key: nextOrcidKey.current++, value: "" }])}>
            <Plus className="size-4" /> Add another ORCID
          </Button>
        </div>
      )}
    </div>
  );
}
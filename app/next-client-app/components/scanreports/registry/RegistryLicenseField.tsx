"use client";

import { InfoIcon } from "lucide-react";
import { Portal as TooltipPortal } from "@radix-ui/react-tooltip";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

// TODO: Replace these temporary options with the licence endpoint response.
const licenses = [
  { id: "CC0-1.0", label: "CC0" },
  { id: "CC-BY-4.0", label: "Attribution" },
  { id: "CC-BY-SA-4.0", label: "Attribution ShareAlike" },
  { id: "ODbL-1.0", label: "Open Database" },
];

interface Props {
  license: string;
  onChange: (license: string) => void;
}

export function RegistryLicenseField({ license, onChange }: Props) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1">
        <Label htmlFor="registry-license">License</Label>
        <TooltipProvider delayDuration={100}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" aria-label="License information" className="ml-1 text-muted-foreground">
                <InfoIcon className="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipPortal>
              <TooltipContent collisionPadding={8} className="max-w-[min(24rem,calc(100vw-2rem))] text-center whitespace-pre-wrap">
                The SPDX licence identifier is included in the prepared publication JSON.
              </TooltipContent>
            </TooltipPortal>
          </Tooltip>
        </TooltipProvider>
      </div>
      <Select value={license} onValueChange={onChange}>
        <SelectTrigger id="registry-license" className="w-full font-normal">
          <SelectValue placeholder="Select a licence..." />
        </SelectTrigger>
        <SelectContent>
          {licenses.map((item) => (
            <SelectItem key={item.id} value={item.id}>
              {item.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
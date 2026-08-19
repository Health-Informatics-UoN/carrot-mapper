"use client";

import { InfoIcon } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export function DescriptionPopover({
  description,
  title = "Description",
}: {
  description: string | null;
  title?: string;
}) {
  if (!description) {
    return null;
  }

  return (
    <Popover>
      <PopoverTrigger
        className="text-muted-foreground hover:text-foreground"
        aria-label={title}
      >
        <InfoIcon className="h-4 w-4" />
      </PopoverTrigger>
      <PopoverContent className="w-96 max-w-[90vw]">
        <p className="text-sm font-medium mb-1">{title}</p>
        <p className="text-sm text-muted-foreground max-h-64 overflow-y-auto whitespace-pre-wrap">
          {description}
        </p>
      </PopoverContent>
    </Popover>
  );
}

"use client";

import { Loader2, LucideIcon, Check, X, CircleSlash } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export interface StatusOption {
  label: string;
  icon: string;
  value: string;
  color: string;
}

export function StatusIcon({
  statusOptions,
  status,
  statusDetails = "",
  disableTooltip = false,
}: {
  statusOptions: StatusOption[];
  status: { value: string };
  statusDetails?: string;
  disableTooltip?: boolean;
}) {
  const statusInfo = statusOptions.find(
    (option) => option.value === status.value
  );

  const iconMap: { [key: string]: LucideIcon } = {
    Loader2,
    Check,
    X,
    CircleSlash,
  };
  const Icon = statusInfo?.icon ? iconMap[statusInfo.icon] : null;

  if (!Icon) {
    return null;
  }

  const iconElement = (
    <div className="flex justify-center">
      <Icon
        className={cn(
          statusInfo?.color,
          "size-4",
          Icon === Loader2 && "animate-spin"
        )}
      />
    </div>
  );

  if (disableTooltip) {
    return iconElement;
  }

  return (
    <TooltipProvider delayDuration={100}>
      <Tooltip>
        <TooltipTrigger asChild>{iconElement}</TooltipTrigger>
        <TooltipContent className="max-w-[500px] text-center">
          <p>
            {status.value === "FAILED" && statusDetails !== ""
              ? statusDetails
              : statusInfo?.label}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

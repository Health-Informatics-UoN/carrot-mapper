"use client";

import { InfoIcon } from "lucide-react";
import { Portal as TooltipPortal } from "@radix-ui/react-tooltip";
import type { RegistryPublishVersions, ReleaseType } from "@/api/registry";
import { Label } from "@/components/ui/label";
import { RequiredIndicator } from "@/components/ui/required-indicator";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/* ---- Interfaces & Constants ---- */

// SemVer release types, with guidance on when to use each for a mapping set.
const RELEASE_TYPES: { value: ReleaseType; label: string; description: string }[] = [
  { value: "major", label: "Major", description: "Mappings removed or changed" },
  { value: "minor", label: "Minor", description: "Mappings added" },
  { value: "patch", label: "Patch", description: "Metadata or small fixes" },
];

// Props for the loaded versions, the selected release type and validation feedback.
interface Props {
  versions: RegistryPublishVersions | null;
  loading: boolean;
  releaseType: ReleaseType | "";
  validationError?: string;
  onChange: (releaseType: ReleaseType) => void;
}

/**
 * Release type selector for publishing a new version of a mapping set.
 *
 * The version itself is derived by the backend from the set's highest
 * existing version, so each option previews the version it would publish.
 * The first publish of a set is always version 1.0.0.
 */
export function RegistryVersionField({ versions, loading, releaseType, validationError, onChange }: Props) {
  const latest = versions?.latest_version ?? null;

  return (
    <div className="min-w-0 space-y-2">
      {/* Release type label, required indicator and information tooltip. */}
      <div className="flex items-center gap-1">
        <Label id="registry-release-type-label">
          Mapping Set Version <RequiredIndicator />
        </Label>
        <TooltipProvider delayDuration={100}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" aria-label="Mapping set version information" className="ml-1 text-muted-foreground">
                <InfoIcon className="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipPortal>
              <TooltipContent collisionPadding={8} className="max-w-[min(24rem,calc(100vw-2rem))] text-center whitespace-pre-wrap">
                Versions follow Semantic Versioning (MAJOR.MINOR.PATCH). Each new version is higher than every
                existing version of this mapping set, including withdrawn ones.
              </TooltipContent>
            </TooltipPortal>
          </Tooltip>
        </TooltipProvider>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading versions...</p>
      ) : !versions ? null : latest === null ? (
        // The first publish has nothing to bump from.
        <p className="text-sm text-muted-foreground">
          This is the first publication of this mapping set: it will be version{" "}
          <strong className="font-semibold text-foreground">{versions.next_versions.major}</strong>.
        </p>
      ) : (
        <>
          {/* One option per release type, previewing the version it would publish. */}
          <div
            role="radiogroup"
            aria-labelledby="registry-release-type-label"
            aria-required="true"
            aria-invalid={!!validationError}
            aria-describedby={validationError ? "registry-release-type-error" : undefined}
            className="grid gap-2 sm:grid-cols-3"
          >
            {RELEASE_TYPES.map((option) => {
              const selected = releaseType === option.value;
              return (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => onChange(option.value)}
                  className={cn(
                    "flex flex-col items-start rounded-md border px-3 py-2 text-left transition-colors",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    selected ? "border-primary bg-primary/5" : "border-input hover:bg-accent",
                  )}
                >
                  <span className="flex w-full items-baseline justify-between gap-2">
                    <span className="text-sm font-medium">{option.label}</span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {versions.next_versions[option.value]}
                    </span>
                  </span>
                  <span className="text-xs text-muted-foreground">{option.description}</span>
                </button>
              );
            })}
          </div>

          <p className="text-xs text-muted-foreground">Latest version: {latest}</p>
        </>
      )}

      {/* Display release type validation errors. */}
      {validationError && (
        <p id="registry-release-type-error" className="text-xs text-destructive">
          {validationError}
        </p>
      )}
    </div>
  );
}

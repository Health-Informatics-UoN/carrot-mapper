"use client";

import { useId } from "react";
import { InfoIcon } from "lucide-react";
import * as RadioGroup from "@radix-ui/react-radio-group";
import { Portal as TooltipPortal } from "@radix-ui/react-tooltip";
import type { RegistryPublishVersions, ReleaseType } from "@/api/registry";
import { RequiredIndicator } from "@/components/ui/required-indicator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/* ---- Interfaces & Constants ---- */

// SemVer release types, with guidance on when to use each for a mapping set.
const RELEASE_TYPES: {
  value: ReleaseType;
  label: string;
  description: string;
}[] = [
    {
      value: "major",
      label: "Major",
      description: "Mappings removed or changed",
    },
    {
      value: "minor",
      label: "Minor",
      description: "Mappings added",
    },
    {
      value: "patch",
      label: "Patch",
      description: "Metadata or small fixes",
    },
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
export function RegistryVersionField({
  versions,
  loading,
  releaseType,
  validationError,
  onChange,
}: Props) {
  const id = useId();
  const labelId = `${id}-label`;
  const errorId = `${id}-error`;
  const latestVersionId = `${id}-latest-version`;

  const latest = versions?.latest_version ?? null;
  const requiresSelection = !loading && !!versions && latest !== null;

  return (
    <div className="min-w-0 space-y-2">
      {/* Field label, required indicator and information tooltip. */}
      <div className="flex items-center gap-1">
        <span id={labelId} className="text-sm font-medium">
          Mapping Set Version{" "}
          {requiresSelection && (
            <span aria-hidden="true">
              <RequiredIndicator />
            </span>
          )}
        </span>

        <TooltipProvider delayDuration={100}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                aria-label="Mapping set version information"
                className={cn(
                  "ml-1 rounded-sm text-muted-foreground",
                  "focus-visible:outline-none",
                  "focus-visible:ring-2 focus-visible:ring-ring",
                  "focus-visible:ring-offset-2",
                )}
              >
                <InfoIcon className="h-4 w-4" aria-hidden="true" />
              </button>
            </TooltipTrigger>

            <TooltipPortal>
              <TooltipContent
                collisionPadding={8}
                className="max-w-[min(24rem,calc(100vw-2rem))] text-center whitespace-pre-wrap"
              >
                Versions follow Semantic Versioning (MAJOR.MINOR.PATCH).
                Each new version is higher than every existing version
                of this mapping set, including withdrawn ones.
              </TooltipContent>
            </TooltipPortal>
          </Tooltip>
        </TooltipProvider>
      </div>

      {loading ? (
        <p role="status" className="text-sm text-muted-foreground">
          Loading versions...
        </p>
      ) : !versions ? null : latest === null ? (
        // The first publish has nothing to bump from.
        <p role="status" className="text-sm text-muted-foreground">
          This is the first publication of this mapping set: it will be
          version{" "}
          <strong className="font-semibold text-foreground">
            {versions.next_versions.major}
          </strong>
          .
        </p>
      ) : (
        <>
          {/* Accessible release type radio group. */}
          <RadioGroup.Root
            value={releaseType}
            onValueChange={(value) => {
              const option = RELEASE_TYPES.find(
                (option) => option.value === value,
              );

              if (option) {
                onChange(option.value);
              }
            }}
            required
            loop
            aria-labelledby={labelId}
            aria-invalid={!!validationError}
            aria-describedby={
              validationError
                ? `${latestVersionId} ${errorId}`
                : latestVersionId
            }
            className="grid gap-2 sm:grid-cols-3"
          >
            {RELEASE_TYPES.map((option) => {
              const optionId = `${id}-${option.value}`;
              const optionLabelId = `${optionId}-label`;
              const optionVersionId = `${optionId}-version`;
              const optionDescriptionId = `${optionId}-description`;

              return (
                <RadioGroup.Item
                  key={option.value}
                  id={optionId}
                  value={option.value}
                  aria-labelledby={`${optionLabelId} ${optionVersionId}`}
                  aria-describedby={optionDescriptionId}
                  className={cn(
                    // Base card styling.
                    "flex min-w-0 cursor-pointer flex-col items-start",
                    "rounded-md border px-3 py-2",
                    "text-left transition-colors",

                    // Keyboard focus styling.
                    "focus-visible:outline-none",
                    "focus-visible:ring-2 focus-visible:ring-ring",
                    "focus-visible:ring-offset-2",

                    // Selected state.
                    "data-[state=checked]:border-primary",
                    "data-[state=checked]:bg-primary/5",

                    // Unselected state.
                    "data-[state=unchecked]:border-input",
                    "data-[state=unchecked]:hover:bg-accent",
                  )}
                >
                  <span className="flex w-full items-center justify-between gap-2">
                    <span className="flex items-center gap-2">
                      {/* Visual selection indicator. */}
                      <span
                        aria-hidden="true"
                        className={cn(
                          "flex h-4 w-4 shrink-0 items-center",
                          "justify-center rounded-full border border-primary",
                        )}
                      >
                        <RadioGroup.Indicator className="h-2 w-2 rounded-full bg-primary" />
                      </span>

                      {/* Release type label. */}
                      <span
                        id={optionLabelId}
                        className="text-sm font-medium"
                      >
                        {option.label}
                      </span>
                    </span>

                    {/* Preview of the next version. */}
                    <span
                      id={optionVersionId}
                      className="font-mono text-xs text-muted-foreground"
                    >
                      {versions.next_versions[option.value]}
                    </span>
                  </span>

                  {/* Release type description. */}
                  <span
                    id={optionDescriptionId}
                    className="mt-1 text-xs text-muted-foreground"
                  >
                    {option.description}
                  </span>
                </RadioGroup.Item>
              );
            })}
          </RadioGroup.Root>

          <p
            id={latestVersionId}
            className="text-xs text-muted-foreground"
          >
            Latest version: {latest}
          </p>
        </>
      )}

      {/* Display and announce release type validation errors. */}
      {validationError && (
        <p
          id={errorId}
          role="alert"
          className="text-xs text-destructive"
        >
          {validationError}
        </p>
      )}
    </div>
  );
}
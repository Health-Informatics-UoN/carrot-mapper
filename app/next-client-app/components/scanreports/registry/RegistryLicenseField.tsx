"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Check, ChevronsUpDown, FileText, InfoIcon } from "lucide-react";
import { Portal as TooltipPortal } from "@radix-ui/react-tooltip";
import { getRegistryLicenses, type RegistryLicense } from "@/api/licenses";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from "@/components/ui/command";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

const RECOMMENDED_LICENSE_IDS = ["CC0-1.0", "CC-BY-4.0", "ODbL-1.0"];

interface Props {
  license: string;
  validationError?: string;
  onChange: (license: string) => void;
}

export function RegistryLicenseField({ license, validationError, onChange }: Props) {
  const [licenses, setLicenses] = useState<RegistryLicense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [openOnly, setOpenOnly] = useState(false);

  useEffect(() => {
    let active = true;
    getRegistryLicenses()
      .then((result) => {
        if (!active) return;
        if (result.ok) setLicenses(result.licenses);
        else setError(result.message);
      })
      .catch(() => {
        if (active) setError("Could not load licences from the Carrot API.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const selectedLicense = licenses.find((item) => item.id === license);
  const filteredLicenses = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return licenses.filter((item) =>
      !item.is_deprecated &&
      (!openOnly || item.is_open) &&
      (item.id.toLowerCase().includes(needle) || item.label.toLowerCase().includes(needle)),
    );
  }, [licenses, search, openOnly]);
  const recommended = RECOMMENDED_LICENSE_IDS.flatMap((id) => filteredLicenses.filter((item) => item.id === id));
  const otherLicenses = filteredLicenses.filter((item) => !RECOMMENDED_LICENSE_IDS.includes(item.id));
  const visibleOtherLicenses = otherLicenses.slice(0, 100);

  return (
    <div className="min-w-0 space-y-2">
      <div className="flex items-center gap-1">
        <Label htmlFor="registry-license">License <span aria-hidden="true" className="text-destructive">*</span></Label>
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
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button id="registry-license" type="button" role="combobox" variant="outline" aria-expanded={open} aria-required="true" aria-invalid={!!validationError} aria-describedby={validationError ? "registry-license-error" : undefined} className="w-full justify-between gap-2 font-normal">
            <span className="flex min-w-0 items-center gap-2">
              <FileText aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
              <span className="truncate">{selectedLicense ? `${selectedLicense.id} — ${selectedLicense.label}` : "Select a licence..."}</span>
            </span>
            <ChevronsUpDown className="size-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[min(24rem,calc(100vw-2rem))] overflow-hidden p-0 shadow-lg" align="end">
          <Command shouldFilter={false}>
            <CommandInput placeholder="Search name or SPDX ID..." value={search} onValueChange={setSearch} />
            <div className="flex items-center gap-2 border-b bg-muted/30 px-3 py-2.5">
              <Checkbox id="registry-open-only" checked={openOnly} onCheckedChange={(checked) => setOpenOnly(checked === true)} />
              <Label htmlFor="registry-open-only">Open licences only</Label>
            </div>
            <CommandList className="max-h-72">
              {loading ? (
                <p className="p-4 text-sm text-muted-foreground">Loading licences...</p>
              ) : error ? (
                <p className="p-4 text-sm text-destructive">{error}</p>
              ) : (
                <>
                  <CommandEmpty>No matching licences found.</CommandEmpty>
                  {recommended.length > 0 && (
                    <CommandGroup heading="Recommended for SSSOM">
                      {recommended.map((item) => (
                        <CommandItem key={item.id} value={item.id} onSelect={() => { onChange(item.id); setOpen(false); }} className="gap-3 px-3 py-2">
                          <span className="flex min-w-0 flex-1 flex-col"><span className="font-medium">{item.id}</span><span className="whitespace-normal text-xs text-muted-foreground">{item.label}</span></span>
                          <Check aria-hidden="true" className={`size-4 shrink-0 ${license === item.id ? "opacity-100" : "opacity-0"}`} />
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  )}
                  {recommended.length > 0 && otherLicenses.length > 0 && <CommandSeparator className="mx-0 my-1" />}
                  {otherLicenses.length > 0 && (
                    <CommandGroup heading="Other licences">
                      {visibleOtherLicenses.map((item) => (
                        <CommandItem key={item.id} value={item.id} onSelect={() => { onChange(item.id); setOpen(false); }} className="gap-3 px-3 py-2">
                          <span className="flex min-w-0 flex-1 flex-col"><span className="font-medium">{item.id}</span><span className="whitespace-normal text-xs text-muted-foreground">{item.label}</span></span>
                          <Check aria-hidden="true" className={`size-4 shrink-0 ${license === item.id ? "opacity-100" : "opacity-0"}`} />
                        </CommandItem>
                      ))}
                      {otherLicenses.length > visibleOtherLicenses.length && (
                        <p className="px-2 py-2 text-xs text-muted-foreground">Refine your search to see more results.</p>
                      )}
                    </CommandGroup>
                  )}
                </>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {error && <p className="flex items-center gap-1 text-xs text-destructive"><AlertCircle className="size-3" />{error}</p>}
      {validationError && <p id="registry-license-error" className="text-xs text-destructive">{validationError}</p>}
    </div>
  );
}
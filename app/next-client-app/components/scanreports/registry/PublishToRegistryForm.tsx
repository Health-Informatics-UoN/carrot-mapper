"use client";

import { useState, type FormEvent } from "react";
import { CloudUpload, Copy, InfoIcon } from "lucide-react";
import { Portal as TooltipPortal } from "@radix-ui/react-tooltip";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { RegistryOrcidFields } from "./RegistryOrcidFields";
import { RegistryLicenseField } from "./RegistryLicenseField";

interface Props {
  scanReportId: string;
  lastPublishedVersion?: string | null;
  onCancel: () => void;
}

export interface PublishToRegistryPayload {
  scan_report_id: number;
  title: string;
  description: string;
  mapping_set_version: string;
  include_author_orcid_ids: boolean;
  license: string;
}

export function PublishToRegistryForm({
  scanReportId,
  lastPublishedVersion,
  onCancel,
}: Props) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [version, setVersion] = useState("");
  const [includeAuthorOrcidIds, setIncludeAuthorOrcidIds] = useState(false);

  const [license, setLicense] = useState("");

  const [prepared, setPrepared] = useState<PublishToRegistryPayload | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const id = Number(scanReportId);
    const payload: PublishToRegistryPayload = {
      scan_report_id: id,
      title: title.trim(),
      description: description.trim(),
      mapping_set_version: version.trim(),
      include_author_orcid_ids: includeAuthorOrcidIds,
      license, // SPDX ID only; the backend owns all licence metadata.
    };
    setPrepared(payload);
    toast.success("Publication JSON prepared. No data has been published yet.");
  };

  const copyPayload = async () => {
    if (!prepared) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(prepared, null, 2));
      toast.success("JSON copied to clipboard.");
    } catch {
      toast.error("Could not copy JSON to clipboard.");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-2">
        <Label htmlFor="registry-title">Title</Label>
        <Input
          id="registry-title"
          value={title}
          onChange={(event) => { setTitle(event.target.value); setPrepared(null); }}
          placeholder="Enter mapping set title"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="registry-description">Description</Label>
        <Textarea
          id="registry-description"
          value={description}
          onChange={(event) => { setDescription(event.target.value); setPrepared(null); }}
          rows={3}
          placeholder="Describe your mapping set..."
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-1">
          <Label htmlFor="registry-version">Mapping Set Version</Label>
          <TooltipProvider delayDuration={100}>
            <Tooltip>
              <TooltipTrigger asChild>
                <button type="button" aria-label="Mapping set version information" className="ml-1 text-muted-foreground">
                  <InfoIcon className="h-4 w-4" />
                </button>
              </TooltipTrigger>
              <TooltipPortal>
                <TooltipContent collisionPadding={8} className="max-w-[min(24rem,calc(100vw-2rem))] text-center whitespace-pre-wrap">
                  The mapping set version must be unique for this mapping set. A previously published version cannot be reused.
                </TooltipContent>
              </TooltipPortal>
            </Tooltip>
          </TooltipProvider>
        </div>
        <Input
          id="registry-version"
          value={version}
          onChange={(event) => { setVersion(event.target.value); setPrepared(null); }}
          placeholder="e.g. 1.0.0"
        />
        {lastPublishedVersion ? (
          <p className="text-xs text-muted-foreground">Last published version: {lastPublishedVersion}</p>
        ) : (
          <p className="text-xs text-muted-foreground">Published version history is not connected yet.</p>
        )}
      </div>

      <RegistryOrcidFields
        includeAuthorOrcidIds={includeAuthorOrcidIds}
        onIncludeChange={(value) => { setIncludeAuthorOrcidIds(value); setPrepared(null); }}
      />

      <RegistryLicenseField
        license={license}
        onChange={(value) => { setLicense(value); setPrepared(null); }}
      />

      {prepared && (
        <div className="space-y-2 rounded-md border bg-muted/30 p-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">Prepared publication JSON (not submitted)</p>
            <Button type="button" size="sm" variant="outline" onClick={copyPayload}>
              <Copy className="size-3.5" /> Copy JSON
            </Button>
          </div>
          <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-all text-xs">
            {JSON.stringify(prepared, null, 2)}
          </pre>
        </div>
      )}
      <DialogFooter className="gap-2 border-t pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
        <Button type="submit">
          <CloudUpload className="size-4" /> Prepare JSON
        </Button>
      </DialogFooter>
    </form>
  );
}

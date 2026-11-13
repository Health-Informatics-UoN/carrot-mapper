"use client";

import { useState } from "react";
import { Formik } from "formik";
import * as Yup from "yup";
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

interface FormValues {
  title: string;
  description: string;
  version: string;
  includeAuthorOrcidIds: boolean;
  license: string;
}

const validationSchema = Yup.object({
  title: Yup.string().trim().required("Title is required."),
  version: Yup.string().trim().required("Mapping set version is required."),
  license: Yup.string().required("License is required."),
});

export function PublishToRegistryForm({
  scanReportId,
  lastPublishedVersion,
  onCancel,
}: Props) {
  const [prepared, setPrepared] = useState<PublishToRegistryPayload | null>(null);

  const handleSubmit = (values: FormValues) => {
    const payload: PublishToRegistryPayload = {
      scan_report_id: Number(scanReportId),
      title: values.title.trim(),
      description: values.description.trim(),
      mapping_set_version: values.version.trim(),
      include_author_orcid_ids: values.includeAuthorOrcidIds,
      license: values.license,
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
    <Formik<FormValues>
      initialValues={{ title: "", description: "", version: "", includeAuthorOrcidIds: false, license: "" }}
      validationSchema={validationSchema}
      onSubmit={(values, { setSubmitting }) => {
        handleSubmit(values);
        setSubmitting(false);
      }}
    >
      {({ values, errors, touched, handleBlur, handleChange, handleSubmit: submitForm, setFieldValue }) => (
        <form onSubmit={submitForm} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="registry-title">Title <span aria-hidden="true" className="text-destructive">*</span></Label>
            <Input
              id="registry-title"
              name="title"
              value={values.title}
              onChange={(event) => { handleChange(event); setPrepared(null); }}
              onBlur={handleBlur}
              aria-required="true"
              aria-invalid={!!(touched.title && errors.title)}
              aria-describedby={touched.title && errors.title ? "registry-title-error" : undefined}
              placeholder="Enter mapping set title"
            />
            {touched.title && errors.title && <p id="registry-title-error" className="text-xs text-destructive">{errors.title}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="registry-description">Description</Label>
            <Textarea
              id="registry-description"
              name="description"
              value={values.description}
              onChange={(event) => { handleChange(event); setPrepared(null); }}
              rows={3}
              placeholder="Describe your mapping set..."
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-1">
              <Label htmlFor="registry-version">Mapping Set Version <span aria-hidden="true" className="text-destructive">*</span></Label>
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
              name="version"
              value={values.version}
              onChange={(event) => { handleChange(event); setPrepared(null); }}
              onBlur={handleBlur}
              aria-required="true"
              aria-invalid={!!(touched.version && errors.version)}
              aria-describedby={touched.version && errors.version ? "registry-version-error" : undefined}
              placeholder="e.g. 1.0.0"
            />
            {touched.version && errors.version && <p id="registry-version-error" className="text-xs text-destructive">{errors.version}</p>}
            {lastPublishedVersion ? (
              <p className="text-xs text-muted-foreground">Last published version: {lastPublishedVersion}</p>
            ) : (
              <p className="text-xs text-muted-foreground">Published version history is not connected yet.</p>
            )}
          </div>

          <RegistryOrcidFields
            includeAuthorOrcidIds={values.includeAuthorOrcidIds}
            onIncludeChange={(value) => { setFieldValue("includeAuthorOrcidIds", value); setPrepared(null); }}
          />

          <RegistryLicenseField
            license={values.license}
            validationError={touched.license ? errors.license : undefined}
            onChange={(value) => { setFieldValue("license", value); setPrepared(null); }}
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
      )}
    </Formik>
  );
}

"use client";

import { useState } from "react";
import { Formik } from "formik";
import * as Yup from "yup";
import { AlertCircle, CloudUpload, InfoIcon } from "lucide-react";
import { Portal as TooltipPortal } from "@radix-ui/react-tooltip";
import { toast } from "sonner";
import {
  publishScanReportToRegistry,
  type PublishToRegistryPayload,
} from "@/api/registry";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { RegistryOrcidFields } from "./RegistryOrcidFields";
import { RegistryLicenseField } from "./RegistryLicenseField";

/* ---- Interfaces & Constants ---- */

// Props required to associate the publication with a Scan Report.
interface Props {
  scanReportId: string;
  lastPublishedVersion?: string | null;
  onCancel: () => void;
}

// Form values used to collect mapping set publication metadata.
interface FormValues {
  title: string;
  description: string;
  version: string;
  includeAuthorOrcidIds: boolean;
  license: string;
}

// Yup schema for validating required fields and input length.
const validationSchema = Yup.object({
  title: Yup.string()
    .trim()
    .max(500, "Title must be 500 characters or fewer.")
    .required("Title is required."),
  version: Yup.string()
    .trim()
    .max(100, "Mapping set version must be 100 characters or fewer.")
    .required("Mapping set version is required."),
  license: Yup.string().required("License is required."),
});

/**
 * Form for publishing a Scan Report's mapping set to the Registry.
 *
 * Collects mapping set metadata, validates user input using Formik and Yup,
 * and submits the publication request to the Registry backend API.
 */
export function PublishToRegistryForm({
  scanReportId,
  lastPublishedVersion,
  onCancel,
}: Props) {
  // Stores API errors returned during publication.
  const [submitError, setSubmitError] = useState("");
  const handleSubmit = async (values: FormValues) => {
    setSubmitError("");

    // Map form values to the backend's expected request structure.
    const payload: PublishToRegistryPayload = {
      title: values.title.trim(),
      description: values.description.trim(),
      set_version: values.version.trim(),
      include_author_orcid_ids: values.includeAuthorOrcidIds,
      license: values.license,
    };

    try {
      const result = await publishScanReportToRegistry(
        scanReportId,
        payload,
      );

      // Display the backend error without closing the dialog.
      if (!result.ok) {
        setSubmitError(result.message);
        return;
      }

      // Confirm that the publication job has been queued.
      toast.success("Publication queued.", {
        description: `Import job: ${result.job.import_job_id}`,
      });

      onCancel();
    } catch {
      // Handle unexpected request or network failures.
      setSubmitError("Could not start publication. Please try again.");
    }
  };

  return (
    <Formik<FormValues>
      // Initialise form state and apply the Yup validation schema.
      initialValues={{
        title: "",
        description: "",
        version: "",
        includeAuthorOrcidIds: false,
        license: "",
      }}
      validationSchema={validationSchema}
      onSubmit={handleSubmit}
    >
      {({
        values,
        errors,
        touched,
        isSubmitting,
        handleBlur,
        handleChange,
        handleSubmit: submitForm,
        setFieldValue,
      }) => (
        <form onSubmit={submitForm} className="space-y-6">

          {/* Display publication errors returned by the backend. */}
          {submitError && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{submitError}</AlertDescription>
            </Alert>
          )}

          {/* Mapping set title and description. */}
          <section className="space-y-4 border-b border-border pb-3">

            {/* Required mapping set title. */}
            <div className="space-y-2">
              <Label htmlFor="registry-title">
                Title{" "}
                <span aria-hidden="true" className="text-destructive">
                  *
                </span>
              </Label>

              <Input
                id="registry-title"
                name="title"
                value={values.title}
                onChange={handleChange}
                onBlur={handleBlur}
                aria-required="true"
                aria-invalid={!!(touched.title && errors.title)}
                aria-describedby={
                  touched.title && errors.title
                    ? "registry-title-error"
                    : undefined
                }
                placeholder="Enter mapping set title"
              />

              {/* Show validation errors after the field has been touched. */}
              {touched.title && errors.title && (
                <p
                  id="registry-title-error"
                  className="text-xs text-destructive"
                >
                  {errors.title}
                </p>
              )}
            </div>

            {/* Optional mapping set description. */}
            <div className="space-y-2">
              <Label htmlFor="registry-description">
                Description
              </Label>

              <Textarea
                id="registry-description"
                name="description"
                value={values.description}
                onChange={handleChange}
                rows={3}
                placeholder="Describe your mapping set..."
              />
            </div>
          </section>

          {/* Mapping set version, licence selection and ORCID preferences. */}
          <section className="-mt-2 space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">

              {/* Mapping set version with uniqueness guidance. */}
              <div className="min-w-0 space-y-2">
                <div className="flex items-center gap-1">
                  <Label htmlFor="registry-version">
                    Mapping Set Version{" "}
                    <span
                      aria-hidden="true"
                      className="text-destructive"
                    >
                      *
                    </span>
                  </Label>

                  {/* Explain version uniqueness through a tooltip. */}
                  <TooltipProvider delayDuration={100}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          type="button"
                          aria-label="Mapping set version information"
                          className="ml-1 text-muted-foreground"
                        >
                          <InfoIcon className="h-4 w-4" />
                        </button>
                      </TooltipTrigger>

                      <TooltipPortal>
                        <TooltipContent
                          collisionPadding={8}
                          className="max-w-[min(24rem,calc(100vw-2rem))] text-center whitespace-pre-wrap"
                        >
                          The mapping set version must be unique for
                          this mapping set. A previously published
                          version cannot be reused.
                        </TooltipContent>
                      </TooltipPortal>
                    </Tooltip>
                  </TooltipProvider>
                </div>

                <Input
                  id="registry-version"
                  name="version"
                  value={values.version}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  aria-required="true"
                  aria-invalid={!!(touched.version && errors.version)}
                  aria-describedby={
                    touched.version && errors.version
                      ? "registry-version-error"
                      : undefined
                  }
                  placeholder="e.g. 1.0.0"
                />

                {/* Display version validation errors. */}
                {touched.version && errors.version && (
                  <p
                    id="registry-version-error"
                    className="text-xs text-destructive"
                  >
                    {errors.version}
                  </p>
                )}

                {/* Show the last published version when available. */}
                {lastPublishedVersion && (
                  <p className="text-xs text-muted-foreground">
                    Last published version: {lastPublishedVersion}
                  </p>
                )}
              </div>

              {/*
                Reusable licence selector.
                Synchronises the selected SPDX ID with Formik state.
              */}
              <RegistryLicenseField
                license={values.license}
                validationError={
                  touched.license ? errors.license : undefined
                }
                onChange={(value) => {
                  setFieldValue("license", value);
                }}
              />
            </div>

            {/*
              Reusable ORCID component.
              Allows users to enable or disable inclusion of author ORCIDs.
            */}
            <RegistryOrcidFields
              includeAuthorOrcidIds={values.includeAuthorOrcidIds}
              onIncludeChange={(value) => {
                setFieldValue("includeAuthorOrcidIds", value);
              }}
            />
          </section>

          {/* Cancel and publication actions. */}
          <DialogFooter className="gap-2 border-t border-border pt-5">
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              Cancel
            </Button>

            {/* Prevent duplicate submissions while publishing. */}
            <Button type="submit" disabled={isSubmitting}>
              <CloudUpload className="size-4" />
              {isSubmitting ? "Publishing..." : "Publish"}
            </Button>
          </DialogFooter>
        </form>
      )}
    </Formik>
  );
}

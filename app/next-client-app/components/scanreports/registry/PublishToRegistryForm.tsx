"use client";

import { useEffect, useState } from "react";
import { Formik } from "formik";
import * as Yup from "yup";
import { AlertCircle, CloudUpload } from "lucide-react";
import { toast } from "sonner";
import {
  getRegistryPublishVersions,
  publishScanReportToRegistry,
  type PublishToRegistryPayload,
  type RegistryPublishVersions,
  type ReleaseType,
} from "@/api/registry";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RequiredIndicator } from "@/components/ui/required-indicator";
import { Textarea } from "@/components/ui/textarea";
import { RegistryOrcidFields } from "./RegistryOrcidFields";
import { RegistryLicenseField } from "./RegistryLicenseField";
import { RegistryVersionField } from "./RegistryVersionField";

/* ---- Interfaces & Constants ---- */

// Props required to associate the publication with a Scan Report.
interface Props {
  scanReportId: string;
  onCancel: () => void;
}

// Form values used to collect mapping set publication metadata.
interface FormValues {
  title: string;
  description: string;
  releaseType: ReleaseType | "";
  includeAuthorOrcidIds: boolean;
  license: string;
}

// Yup schema for validating required fields and input length.
// The first publish is always 1.0.0, so a release type is only needed after it.
const buildValidationSchema = (requireReleaseType: boolean) =>
  Yup.object({
    title: Yup.string()
      .trim()
      .max(500, "Title must be 500 characters or fewer.")
      .required("Title is required."),
    releaseType: requireReleaseType
      ? Yup.string().required("Choose the kind of release.")
      : Yup.string(),
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
  onCancel,
}: Props) {
  // Stores API errors returned during publication.
  const [submitError, setSubmitError] = useState("");

  // The set's latest version and the version each release type would publish.
  const [versions, setVersions] = useState<RegistryPublishVersions | null>(null);
  const [versionsLoading, setVersionsLoading] = useState(true);
  const [versionsError, setVersionsError] = useState("");
  const isFirstPublish = versions?.latest_version === null;

  // Fetch the versions when the form mounts.
  // Ignore responses after unmounting to avoid stale state updates.
  useEffect(() => {
    let active = true;
    getRegistryPublishVersions(scanReportId)
      .then((result) => {
        if (!active) return;
        if (result.ok) setVersions(result.versions);
        else setVersionsError(result.message);
      })
      .catch(() => {
        if (active) setVersionsError("Could not load the mapping set's versions.");
      })
      .finally(() => {
        if (active) setVersionsLoading(false);
      });
    return () => { active = false; };
  }, [scanReportId]);

  const handleSubmit = async (values: FormValues) => {
    setSubmitError("");

    // Map form values to the backend's expected request structure.
    // Any release type gives 1.0.0 for the first publish.
    const payload: PublishToRegistryPayload = {
      title: values.title.trim(),
      description: values.description.trim(),
      release_type: values.releaseType || "major",
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
      toast.success(`Publication of version ${result.job.set_version} queued.`, {
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
        releaseType: "",
        includeAuthorOrcidIds: false,
        license: "",
      }}
      validationSchema={buildValidationSchema(!isFirstPublish)}
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

          {/* Display version loading and publication errors returned by the backend. */}
          {(versionsError || submitError) && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{submitError || versionsError}</AlertDescription>
            </Alert>
          )}

          {/* Mapping set title and description. */}
          <section className="space-y-4 border-b border-border pb-3">

            {/* Required mapping set title. */}
            <div className="space-y-2">
              <Label htmlFor="registry-title">
                Title <RequiredIndicator />
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

            {/*
              SemVer release type selector.
              The backend derives the version from the set's highest version.
            */}
            <RegistryVersionField
              versions={versions}
              loading={versionsLoading}
              releaseType={values.releaseType}
              validationError={
                touched.releaseType ? errors.releaseType : undefined
              }
              onChange={(value) => {
                setFieldValue("releaseType", value);
              }}
            />

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

            {/* Prevent duplicate submissions, and publishing before the versions are known. */}
            <Button type="submit" disabled={isSubmitting || !versions}>
              <CloudUpload className="size-4" />
              {isSubmitting ? "Publishing..." : "Publish"}
            </Button>
          </DialogFooter>
        </form>
      )}
    </Formik>
  );
}

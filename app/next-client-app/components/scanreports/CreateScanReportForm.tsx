"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertCircle, Upload } from "lucide-react";
import {
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { Switch } from "@/components/ui/switch";
import { Formik } from "formik";
import { toast } from "sonner";
import { FormDataFilter } from "../form-components/FormikUtils";
import { FormikSelect } from "../form-components/FormikSelect";
import { FormikSelectDataset } from "../form-components/FormikSelectDataset";
import { FormikSelectEditors } from "../form-components/FormikSelectEditors";
import { createScanReport } from "@/api/scanreports";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useState } from "react";
import { CreateDatasetDialog } from "../datasets/CreateDatasetDialog";
import * as Yup from "yup";
import { MAX_FILE_SIZE_BYTES } from "@/constants";

interface FormData {
  name: string;
  visibility: string;
  viewers: number[];
  editors: number[];
  dataset: number;
  scan_report_file: File | null;
  Data_dict: File | null;
}

// Yup validation schema
const validationSchema = Yup.object({
  name: Yup.string().required("Scan report name is required"),
  scan_report_file: Yup.mixed()
    .required("Scan report file is required")
    .test(
      "fileSize",
      `File size must be less than ${MAX_FILE_SIZE_BYTES / 1024 / 1024}MB`,
      function (value) {
        if (!value) return false; // Don't allow null/undefined
        const file = value as File;
        return file.size <= MAX_FILE_SIZE_BYTES;
      }
    ),
  Data_dict: Yup.mixed()
    .nullable()
    .test(
      "fileSize",
      `File size must be less than ${MAX_FILE_SIZE_BYTES / 1024 / 1024}MB`,
      function (value) {
        if (!value) return true;
        const file = value as File;
        return file.size <= MAX_FILE_SIZE_BYTES;
      }
    ),
});

export function CreateScanReportForm({
  dataPartners,
  projects,
}: {
  dataPartners: DataPartner[];
  projects: Project[];
}) {
  const [error, setError] = useState<string | null>(null);
  const partnerOptions = FormDataFilter<DataPartner>(dataPartners);
  const [reloadDataset, setReloadDataset] = useState(false);
  // State to hide/show the viewers field
  const [publicVisibility, setPublicVisibility] = useState<boolean>(true);
  const maxFileSizeMB = MAX_FILE_SIZE_BYTES / 1024 / 1024;

  const handleSubmit = async (data: FormData) => {
    const formData = new FormData();
    formData.append("dataset", data.name);
    formData.append("visibility", data.visibility);
    formData.append("parent_dataset", data.dataset.toString());
    data.viewers.forEach((viewer) => {
      formData.append("viewers", viewer.toString());
    });
    data.editors.forEach((editor) => {
      formData.append("editors", editor.toString());
    });
    if (data.scan_report_file) {
      formData.append("scan_report_file", data.scan_report_file);
    }
    if (data.Data_dict) {
      formData.append("data_dictionary_file", data.Data_dict);
    }

    const response = await createScanReport(formData);

    if (response) {
      setError(response.errorMessage);
      toast.error("Upload New Scan Report failed. Fix the error(s) first");
    } else {
      toast.dismiss();
      setError(null);
    }
  };

  return (
    <>
      {error && (
        <Alert variant="destructive" className="mb-3 max-w-2xl">
          <AlertTitle className="flex items-center">
            <AlertCircle className="h-4 w-4 mr-2" />
            Upload New Scan Report Failed. Error:
          </AlertTitle>
          <AlertDescription>
            <ul>
              {error.split(" * ").map((err, index) => (
                <li key={index}>* {err}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      <Formik
        initialValues={{
          dataPartner: 0,
          dataset: 0,
          viewers: [],
          editors: [],
          visibility: "PUBLIC",
          name: "",
          scan_report_file: null,
          Data_dict: null,
        }}
        validationSchema={validationSchema}
        validateOnChange={false}
        validateOnBlur={false}
        onSubmit={(data) => {
          toast.info("Validating and uploading...");
          handleSubmit(data);
        }}
      >
        {({ values, handleChange, handleSubmit, setFieldValue }) => (
          <form
            className="w-full max-w-2xl"
            onSubmit={handleSubmit}
            encType="multipart/form-data"
          >
            <div className="flex flex-col gap-5">
              <FormField name="name">
                {({ field }) => (
                  <FormItem>
                    <FormLabel>Scan Report Name</FormLabel>
                    <FormDescription>
                      Name of the new Scan Report.
                    </FormDescription>
                    <FormControl>
                      <Input {...field} onChange={handleChange} name="name" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              </FormField>

              <FormItem>
                <FormLabel>Data Partner</FormLabel>
                <FormDescription>
                  The Data Partner that owns the Dataset of the new Scan Report.
                </FormDescription>
                <FormControl>
                  <FormikSelect
                    options={partnerOptions}
                    name="dataPartner"
                    placeholder="Choose a Data Partner"
                    isMulti={false}
                    isDisabled={false}
                    required={true}
                  />
                </FormControl>
              </FormItem>

              <FormItem>
                <div className="flex items-center">
                  <FormLabel>Dataset</FormLabel>
                  {values.dataPartner !== 0 && (
                    <div className="flex ml-2">
                      <CreateDatasetDialog
                        projects={projects}
                        dataPartnerID={values.dataPartner}
                        description={true}
                        setReloadDataset={setReloadDataset}
                      />
                    </div>
                  )}
                </div>
                <FormDescription>
                  The Dataset to add the new Scan Report to.
                </FormDescription>
                <FormControl>
                  <FormikSelectDataset
                    name="dataset"
                    placeholder={
                      values.dataPartner
                        ? "Choose a Dataset"
                        : "To choose a dataset, please select a Data partner"
                    }
                    isMulti={false}
                    isDisabled={values.dataPartner === 0}
                    required={true}
                    reloadDataset={reloadDataset}
                  />
                </FormControl>
              </FormItem>

              <FormField name="visibility">
                {({ field }) => (
                  <FormItem>
                    <div className="flex items-center space-x-3">
                      <FormLabel>Visibility</FormLabel>
                      <FormControl>
                        <Switch
                          onCheckedChange={(checked) => {
                            handleChange({
                              target: {
                                name: "visibility",
                                value: checked ? "PUBLIC" : "RESTRICTED",
                              },
                            });
                            setPublicVisibility(checked);
                          }}
                          checked={values.visibility === "PUBLIC"}
                        />
                      </FormControl>
                      <span className="text-sm">
                        {/* Show user-friendly label */}
                        {values.visibility === "PUBLIC"
                          ? "Shared"
                          : "Restricted"}
                      </span>
                    </div>
                    <FormDescription>
                      Setting the visibility of the new Scan Report.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              </FormField>

              {!publicVisibility && (
                <FormItem>
                  <FormLabel>Viewers</FormLabel>
                  <FormDescription>
                    If the Scan Report is shared, then all users with access to
                    the Dataset have viewer access to the Scan Report.
                    Additionally, Dataset admins and editors have viewer access
                    to the Scan Report in all cases.
                  </FormDescription>
                  <FormControl>
                    <FormikSelectEditors
                      name="viewers"
                      placeholder={
                        values.dataset
                          ? "Choose viewers"
                          : "To choose viewers, please select a Dataset"
                      }
                      isMulti={true}
                      isDisabled={values.dataset === 0 || values.dataset === -1}
                    />
                  </FormControl>
                </FormItem>
              )}

              <FormItem>
                <FormLabel>Editors</FormLabel>
                <FormDescription>
                  Dataset admins and editors also have Scan Report editor
                  permissions.
                </FormDescription>
                <FormControl>
                  <FormikSelectEditors
                    name="editors"
                    placeholder={
                      values.dataset
                        ? "Choose editors"
                        : "To choose editors, please select a Dataset"
                    }
                    isMulti={true}
                    isDisabled={values.dataset === 0 || values.dataset === -1}
                  />
                </FormControl>
              </FormItem>

              <FormField name="scan_report_file">
                {({ field }) => (
                  <FormItem>
                    <FormLabel>
                      <div className="flex items-center gap-2">
                        WhiteRabbit Scan Report{" "}
                        <span className="text-muted-foreground text-sm">
                          (.xlsx file, required, max {maxFileSizeMB}MB)
                        </span>
                      </div>
                    </FormLabel>
                    <FormDescription>
                      Scan Report file generated from White Rabbit application.
                    </FormDescription>
                    <FormControl>
                      <Input
                        type="file"
                        name="scan_report_file"
                        accept=".xlsx"
                        onChange={(e) => {
                          if (e.currentTarget.files) {
                            setFieldValue(
                              "scan_report_file",
                              e.currentTarget.files[0]
                            );
                          }
                        }}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              </FormField>

              <FormField name="Data_dict">
                {({ field }) => (
                  <FormItem>
                    <FormLabel>
                      <div className="flex items-center gap-2">
                        Data Dictionary{" "}
                        <span className="text-muted-foreground text-sm">
                          (.csv file, optional, max {maxFileSizeMB}MB)
                        </span>
                      </div>
                    </FormLabel>
                    <FormDescription>
                      Optional data dictionary to enable automatic building
                      concepts from OMOP vocabulary.
                    </FormDescription>
                    <FormControl>
                      <Input
                        type="file"
                        name="Data_dict"
                        accept=".csv"
                        onChange={(e) => {
                          if (e.currentTarget.files) {
                            setFieldValue(
                              "Data_dict",
                              e.currentTarget.files[0]
                            );
                          }
                        }}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              </FormField>

              <div className="mb-5 mt-3 flex">
                <Button
                  type="submit"
                  disabled={
                    values.dataPartner === 0 ||
                    values.dataset === 0 ||
                    values.dataset === -1 ||
                    values.name === ""
                  }
                >
                  <Upload />
                  Upload Scan Report
                </Button>
              </div>
            </div>
          </form>
        )}
      </Formik>
    </>
  );
}

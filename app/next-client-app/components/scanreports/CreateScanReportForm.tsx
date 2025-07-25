"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertCircle, Upload } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Form, Formik, Field, ErrorMessage } from "formik";
import { toast } from "sonner";
import { FormDataFilter } from "../form-components/FormikUtils";
import { Tooltips } from "../core/Tooltips";
import { FormikSelect } from "../form-components/FormikSelect";
import { FormikSelectDataset } from "../form-components/FormikSelectDataset";
import { FormikSelectEditors } from "../form-components/FormikSelectEditors";
import { createScanReport } from "@/api/scanreports";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useState } from "react";
import { CreateDatasetDialog } from "../datasets/CreateDatasetDialog";
import * as Yup from "yup";

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
  name: Yup.string().required("Scan Report name is required"),
  dataPartner: Yup.number().min(1, "Please select a Data Partner"),
  dataset: Yup.number().min(1, "Please select a Dataset"),
  scan_report_file: Yup.mixed()
    .required("Scan Report file is required")
    .test("fileSize", "File size must be less than 20MB", function (value) {
      if (!value) return true;
      const file = value as File;
      return file.size <= 20 * 1024 * 1024;
    })
    .test("fileType", "Only .xlsx files are allowed", function (value) {
      if (!value) return true;
      const file = value as File;
      const allowedTypes = [".xlsx"];
      const fileExtension = file.name.split(".").pop()?.toLowerCase();
      if (!fileExtension || !allowedTypes.includes(`.${fileExtension}`)) {
        return this.createError({
          message: `File type .${fileExtension} is not allowed. Only .xlsx files are accepted.`
        });
      }
      return true;
    }),
  Data_dict: Yup.mixed()
    .test("fileSize", "File size must be less than 20MB", function (value) {
      if (!value) return true; // Optional field
      const file = value as File;
      return file.size <= 20 * 1024 * 1024;
    })
    .test("fileType", "Only .csv files are allowed", function (value) {
      if (!value) return true; // Optional field
      const file = value as File;
      const allowedTypes = [".csv"];
      const fileExtension = file.name.split(".").pop()?.toLowerCase();
      if (!fileExtension || !allowedTypes.includes(`.${fileExtension}`)) {
        return this.createError({
          message: `File type .${fileExtension} is not allowed. Only .csv files are accepted.`
        });
      }
      return true;
    })
});

export function CreateScanReportForm({
  dataPartners,
  projects
}: {
  dataPartners: DataPartner[];
  projects: Project[];
}) {
  const [error, setError] = useState<string | null>(null);
  const partnerOptions = FormDataFilter<DataPartner>(dataPartners);
  const [reloadDataset, setReloadDataset] = useState(false);
  // State to hide/show the viewers field
  const [publicVisibility, setPublicVisibility] = useState<boolean>(true);

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
      toast.success("New Scan Report is being uploaded");
      setError(null);
    }
  };

  return (
    <>
      {error && (
        <Alert variant="destructive" className="mb-3">
          <div>
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
          </div>
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
          Data_dict: null
        }}
        validationSchema={validationSchema}
        onSubmit={(data) => {
          toast.info("Validating ...");
          handleSubmit(data);
        }}
      >
        {({
          values,
          handleChange,
          handleSubmit,
          setFieldValue,
          errors,
          touched
        }) => (
          <Form
            className="w-full"
            onSubmit={handleSubmit}
            encType="multipart/form-data"
          >
            <div className="flex flex-col gap-3 text-lg">
              <div className="flex flex-col gap-2">
                <h3 className="flex">
                  {" "}
                  Scan Report Name
                  <Tooltips content="Name of the new Scan Report." />
                </h3>
                <Field
                  as={Input}
                  name="name"
                  className="text-lg"
                  required={true}
                />
                <ErrorMessage
                  name="name"
                  component="div"
                  className="text-destructive text-sm"
                />
              </div>
              <div className="flex flex-col gap-2">
                <h3 className="flex">
                  Data Partner{" "}
                  <Tooltips
                    content="The Data Partner that owns the Dataset of the new Scan Report."
                    link="https://carrot4omop.ac.uk/Carrot-Mapper/projects-datasets-and-scanreports/#access-controls"
                  />
                </h3>
                <FormikSelect
                  options={partnerOptions}
                  name="dataPartner"
                  placeholder="Choose a Data Partner"
                  isMulti={false}
                  isDisabled={false}
                  required={true}
                />
                <ErrorMessage
                  name="dataPartner"
                  component="div"
                  className="text-destructive text-sm"
                />
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-center">
                  <h3 className="flex">
                    {" "}
                    Dataset
                    <Tooltips
                      content="The Dataset to add the new Scan Report to."
                      link="https://carrot4omop.ac.uk/Carrot-Mapper/projects-datasets-and-scanreports/#access-controls"
                    />
                  </h3>
                  {values.dataPartner !== 0 && (
                    <div className="flex">
                      <CreateDatasetDialog
                        projects={projects}
                        dataPartnerID={values.dataPartner}
                        description={true}
                        setReloadDataset={setReloadDataset}
                      />
                      <Tooltips content="If you couldn't find a dataset you wanted, you can create a new dataset here" />
                    </div>
                  )}
                </div>
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
                <ErrorMessage
                  name="dataset"
                  component="div"
                  className="text-destructive text-sm"
                />
              </div>
              <div className="flex items-center space-x-3">
                <h3 className="flex">
                  Visibility
                  <Tooltips
                    content="Setting the visibility of the new Scan Report."
                    link="https://carrot4omop.ac.uk/Carrot-Mapper/projects-datasets-and-scanreports/#access-controls"
                  />
                </h3>
                <Switch
                  onCheckedChange={(checked) => {
                    handleChange({
                      target: {
                        name: "visibility",
                        value: checked ? "PUBLIC" : "RESTRICTED"
                      }
                    });
                    setPublicVisibility(checked);
                  }}
                  checked={values.visibility === "PUBLIC"}
                />
                <Label className="text-lg">
                  {/* Show user-friendly label */}
                  {values.visibility === "PUBLIC" ? "Shared" : "Restricted"}
                </Label>
              </div>
              {!publicVisibility && (
                <div className="flex flex-col gap-2">
                  <h3 className="flex">
                    {" "}
                    Viewers
                    <Tooltips content="If the Scan Report is shared, then all users with access to the Dataset have viewer access to the Scan Report. Additionally, Dataset admins and editors have viewer access to the Scan Report in all cases." />
                  </h3>
                  {/* Viewers field uses the same logic and data as Editors field */}
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
                </div>
              )}
              <div className="flex flex-col gap-2">
                <h3 className="flex">
                  {" "}
                  Editors
                  <Tooltips
                    content="Dataset admins and editors also have Scan Report editor permissions."
                    link="https://carrot4omop.ac.uk/Carrot-Mapper/projects-datasets-and-scanreports/#scan-report-roles"
                  />
                </h3>
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
              </div>
              <div className="flex flex-col gap-2">
                <h3 className="flex">
                  <div className="flex items-center gap-2">
                    WhiteRabbit Scan Report{" "}
                    <span className="text-muted-foreground text-sm">
                      (.xlsx file, max 20MB)
                    </span>
                  </div>
                  <Tooltips
                    content="Scan Report file generated from White Rabbit application."
                    link="https://carrot4omop.ac.uk/Carrot-Mapper/uploading-scan-report/#the-scan-report-file-format"
                  />
                </h3>
                <div>
                  <Field
                    name="scan_report_file"
                    render={({ field, form }: any) => (
                      <Input
                        type="file"
                        accept=".xlsx"
                        required={true}
                        onChange={(e) => {
                          if (
                            e.currentTarget.files &&
                            e.currentTarget.files[0]
                          ) {
                            const file = e.currentTarget.files[0];
                            if (file.size > 20 * 1024 * 1024) {
                              toast.error("File size exceeds 20MB limit");
                            }
                            form.setFieldValue("scan_report_file", file);
                          }
                        }}
                      />
                    )}
                  />
                </div>
                <ErrorMessage
                  name="scan_report_file"
                  component="div"
                  className="text-destructive text-sm"
                />
              </div>

              <div className="flex flex-col gap-2">
                <h3 className="flex">
                  <div className="flex items-center gap-2">
                    Data Dictionary{" "}
                    <span className="text-muted-foreground text-sm">
                      (.csv file, optional, max 20MB)
                    </span>
                  </div>
                  <Tooltips
                    content="Optional data dictionary to enable automatic building concepts from OMOP vocalubary."
                    link="https://carrot4omop.ac.uk/Carrot-Mapper/uploading-scan-report/#the-data-dictionary-file-format"
                  />
                </h3>
                <div>
                  <Field
                    name="Data_dict"
                    render={({ field, form }: any) => (
                      <Input
                        type="file"
                        accept=".csv"
                        onChange={(e) => {
                          if (
                            e.currentTarget.files &&
                            e.currentTarget.files[0]
                          ) {
                            const file = e.currentTarget.files[0];
                            if (file.size > 20 * 1024 * 1024) {
                              toast.error("File size exceeds 20MB limit");
                            }
                            form.setFieldValue("Data_dict", file);
                          }
                        }}
                      />
                    )}
                  />
                </div>
                <ErrorMessage
                  name="Data_dict"
                  component="div"
                  className="text-destructive text-sm"
                />
              </div>
              <div className="mb-5 mt-3 flex">
                <Button
                  type="submit"
                  className="px-4 py-2 text-lg border border-input"
                  disabled={
                    values.dataPartner === 0 ||
                    values.dataset === 0 ||
                    values.dataset === -1 ||
                    values.name === "" ||
                    Object.keys(errors).length > 0
                  }
                >
                  <Upload className="mr-2" />
                  Upload Scan Report
                </Button>
                <Tooltips content="You must be either an admin or an editor of the parent dataset to add a new scan report to it." />
              </div>
            </div>
          </Form>
        )}
      </Formik>
    </>
  );
}

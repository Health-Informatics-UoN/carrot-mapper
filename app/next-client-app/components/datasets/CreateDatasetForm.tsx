"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertCircle, SquarePlus } from "lucide-react";
import { FormField, FormItem, FormLabel, FormControl, FormMessage, FormDescription } from "@/components/ui/form";
import { Switch } from "@/components/ui/switch";
import { Formik } from "formik";
import { toast } from "sonner";
import { FormDataFilter } from "../form-components/FormikUtils";
import { FormikSelect } from "../form-components/FormikSelect";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useState } from "react";
import { FormikSelectUsers } from "../form-components/FormikSelectUsers";
import { createDataset } from "@/api/datasets";

interface FormData {
  name: string;
  visibility: string;
  viewers: number[];
  editors: number[];
  admins: number[];
  dataPartner: number;
  projects: number;
}

export function CreateDatasetForm({
  dataPartnerID,
  dataPartnerList,
  projectList,
  setDialogOpened,
  setReloadDataset,
}: {
  dataPartnerID?: number;
  dataPartnerList?: DataPartner[];
  projectList: Project[];
  setDialogOpened: (dialogOpened: boolean) => void;
  setReloadDataset?: (reloadDataset: boolean) => void;
}) {
  const [publicVisibility, setPublicVisibility] = useState<boolean>(true);

  const partnerOptions = FormDataFilter<DataPartner>(dataPartnerList || []);
  const projectOptions = FormDataFilter<Project>(projectList || []);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: FormData) => {
    const submittingData = {
      name: data.name,
      visibility: data.visibility,
      data_partner: data.dataPartner,
      viewers: data.viewers || [],
      admins: data.admins || [],
      editors: data.editors || [],
      projects: data.projects || [],
    };

    const response = await createDataset(submittingData);

    if (response) {
      setError(response.errorMessage);
      toast.error("Add New Dataset failed. Fix the error(s) first");
    } else {
      toast.success("New Dataset created!");
      setError(null);
      setDialogOpened(false);
      // When a new dataset created, close the dialog then reload the dataset options
      if (setReloadDataset) {
        setReloadDataset(true);
        // After 1s, set reloadDataset to false again, in order to add again the other datasets, if needed
        setTimeout(() => {
          setReloadDataset(false);
        }, 1000);
      }
    }
  };

  return (
    <>
      {error && (
        <Alert variant="destructive" className="mb-3">
          <div>
            <AlertTitle className="flex items-center">
              <AlertCircle className="h-4 w-4 mr-2" />
              Add New Dataset Failed. Error:
            </AlertTitle>
            <AlertDescription>
              <ul>
                {error.split(" * ").map((err, index) => (
                  <li key={index}>* {err}</li>
                ))}
                <li>* Notice: The name of dataset should be unique *</li>
              </ul>
            </AlertDescription>
          </div>
        </Alert>
      )}
      <Formik
        initialValues={{
          dataPartner: dataPartnerID ? dataPartnerID : 0,
          viewers: [],
          editors: [],
          admins: [],
          visibility: "PUBLIC", // Always use "PUBLIC" or "RESTRICTED" for backend compatibility
          name: "",
          projects: 0,
        }}
        onSubmit={(data) => {
          toast.info("Creating Dataset ...");
          handleSubmit(data);
        }}
      >
        {({ values, handleChange, handleSubmit }) => (
          <form className="w-full" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-3 text-lg">
                            {!dataPartnerID && (
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
              )}
              
              <FormField name="name">
                {({ field }) => (
                  <FormItem>
                    <FormLabel>Dataset Name</FormLabel>
                    <FormDescription>
                      Name of the new Dataset.
                    </FormDescription>
                    <FormControl>
                      <Input
                        {...field}
                        onChange={handleChange}
                        name="name"
                        required
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              </FormField>

              <FormItem>
                <FormLabel>Projects</FormLabel>
                <FormDescription>
                  A Project is the highest-level object. A single Dataset may live in more than one Project.
                </FormDescription>
                <FormControl>
                  <FormikSelect
                    options={projectOptions}
                    name="projects"
                    placeholder="Select Projects"
                    isMulti={true}
                    isDisabled={false}
                    required={true}
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
                          defaultChecked
                        />
                      </FormControl>
                      <span className="text-lg">
                        {/* Show user-friendly label */}
                        {values.visibility === "PUBLIC" ? "Shared" : "Restricted"}
                      </span>
                    </div>
                    <FormDescription>
                      If a Dataset is shared, then all users with access to any project associated to the Dataset will have Dataset viewer permissions.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              </FormField>

              {!publicVisibility && (
                <FormItem>
                  <FormLabel>Viewers</FormLabel>
                  <FormDescription>
                    Members of the chosen projects above. All Dataset admins and editors also have Dataset viewer permissions.
                  </FormDescription>
                  <FormControl>
                    <FormikSelectUsers
                      name="viewers"
                      placeholder={
                        values.projects
                          ? "Choose viewers"
                          : "To choose viewers, please select at least one Project"
                      }
                      isMulti={true}
                      isDisabled={values.projects === 0}
                    />
                  </FormControl>
                </FormItem>
              )}

              <FormItem>
                <FormLabel>Editors</FormLabel>
                <FormDescription>
                  Members of the chosen projects above. Dataset admins and editors also have Scan Report editor permissions.
                </FormDescription>
                <FormControl>
                  <FormikSelectUsers
                    name="editors"
                    placeholder={
                      values.projects
                        ? "Choose editors"
                        : "To choose editors, please select at least one Project"
                    }
                    isMulti={true}
                    isDisabled={values.projects === 0}
                  />
                </FormControl>
              </FormItem>

              <FormItem>
                <FormLabel>Admins</FormLabel>
                <FormDescription>
                  Members of the chosen projects above. Dataset admins and editors also have Scan Report editor permissions.
                </FormDescription>
                <FormControl>
                  <FormikSelectUsers
                    name="admins"
                    placeholder={
                      values.projects
                        ? "Choose admins"
                        : "To choose admins, please select at least one Project"
                    }
                    isMulti={true}
                    isDisabled={values.projects === 0}
                  />
                </FormControl>
              </FormItem>

              <div className="mb-5">
                <Button
                  type="submit"
                  className="px-4 py-2 mt-3 text-lg border border-input"
                  disabled={
                    values.dataPartner === 0 ||
                    values.name === "" ||
                    values.projects === 0
                  }
                >
                  Create Dataset
                  <SquarePlus className="ml-2" />
                </Button>
              </div>
            </div>
          </form>
        )}
      </Formik>
    </>
  );
}

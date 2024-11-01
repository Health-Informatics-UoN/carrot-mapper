"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertCircle, SquarePlus } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Form, Formik } from "formik";
import { toast } from "sonner";
import { FormDataFilter } from "../form-components/FormikUtils";
import { Tooltips } from "../Tooltips";
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
          visibility: "PUBLIC",
          name: "",
          projects: 0,
        }}
        onSubmit={(data) => {
          toast.info("Creating Dataset ...");
          handleSubmit(data);
        }}
      >
        {({ values, handleChange, handleSubmit }) => (
          <Form className="w-full" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-3 text-lg">
              {!dataPartnerID && (
                <>
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
                  </div>
                </>
              )}
              <div className="flex flex-col gap-2">
                <h3 className="flex">
                  {" "}
                  Dataset Name
                  <Tooltips content="Name of the new Dataset." />
                </h3>
                <Input
                  onChange={handleChange}
                  name="name"
                  className="text-lg text-carrot"
                  required
                />
              </div>
              <div className="flex flex-col gap-2">
                <h3 className="flex items-center">
                  {" "}
                  Projects
                  <Tooltips
                    content="A Project is the highest-level object. A single Dataset may live in more than one Project."
                    link="https://carrot4omop.ac.uk/Carrot-Mapper/projects-datasets-and-scanreports/"
                  />
                </h3>
                <FormikSelect
                  options={projectOptions}
                  name="projects"
                  placeholder="Select Projects"
                  isMulti={true}
                  isDisabled={false}
                  required={true}
                />
              </div>
              <div className="flex items-center space-x-3">
                <h3 className="flex">
                  Visibility
                  <Tooltips
                    content="If a Dataset is PUBLIC, then all users with access to any project associated to the Dataset will have Dataset viewer permissions."
                    link="https://carrot4omop.ac.uk/Carrot-Mapper/projects-datasets-and-scanreports/#access-controls"
                  />
                </h3>
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
                <Label className="text-lg">
                  {values.visibility === "PUBLIC" ? "PUBLIC" : "RESTRICTED"}
                </Label>
              </div>
              {!publicVisibility && (
                <div className="flex flex-col gap-2">
                  <h3 className="flex">
                    {" "}
                    Viewers
                    <Tooltips
                      content="Members of the chosen projects above. All Dataset admins and editors also have Dataset viewer permissions."
                      link="https://carrot4omop.ac.uk/Carrot-Mapper/projects-datasets-and-scanreports/#access-controls"
                    />
                  </h3>
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
                </div>
              )}
              <div className="flex flex-col gap-2">
                <h3 className="flex">
                  {" "}
                  Editors
                  <Tooltips
                    content="Members of the chosen projects above. Dataset admins and editors also have Scan Report editor permissions."
                    link="https://carrot4omop.ac.uk/Carrot-Mapper/projects-datasets-and-scanreports/#access-controls"
                  />
                </h3>
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
              </div>
              <div className="flex flex-col gap-2">
                <h3 className="flex">
                  {" "}
                  Admins
                  <Tooltips
                    content="Members of the chosen projects above. Dataset admins and editors also have Scan Report editor permissions."
                    link="https://carrot4omop.ac.uk/Carrot-Mapper/projects-datasets-and-scanreports/#access-controls"
                  />
                </h3>
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
              </div>
              <div className="mb-5">
                <Button
                  type="submit"
                  className="px-4 py-2 mt-3 bg-carrot text-white rounded text-lg"
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
          </Form>
        )}
      </Formik>
    </>
  );
}

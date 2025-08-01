"use client";

import { updateDatasetDetails } from "@/api/datasets";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Save } from "lucide-react";
import { FormField, FormItem, FormLabel, FormControl, FormMessage, FormDescription } from "@/components/ui/form";
import { Switch } from "@/components/ui/switch";
import { Formik } from "formik";
import { toast } from "sonner";
import { FindAndFormat, FormDataFilter } from "../form-components/FormikUtils";
import { FormikSelect } from "../form-components/FormikSelect";
import { useState } from "react";

interface FormData {
  name: string;
  visibility: string;
  dataPartner: number;
  viewers: number[];
  editors: number[];
  admins: number[];
  projects: number[];
}

export function DatasetForm({
  dataset,
  dataPartners,
  projects,
  users,
  permissions,
}: {
  dataset: DataSetSRList;
  dataPartners: DataPartner[];
  users: User[];
  projects: Project[];
  permissions: Permission[];
}) {
  // Permissions
  const canUpdate = permissions.includes("CanAdmin");
  // State control for viewers fields
  const [publicVisibility, setPublicVisibility] = useState<boolean>(
    dataset.visibility === "PUBLIC" ? true : false
  );

  // Making options suitable for React Select
  const userOptions = FormDataFilter<User>(users);
  const partnerOptions = FormDataFilter<DataPartner>(dataPartners);
  const projectOptions = FormDataFilter<Project>(projects);
  // Find the intial data partner which is required when adding Dataset
  const initialPartner = dataPartners.find(
    (partner) => dataset.data_partner.id === partner.id
  )!;
  // Find and make initial data suitable for React select
  const initialPartnerFilter = FormDataFilter<DataPartner>(initialPartner);
  const initialViewersFilter = FormDataFilter<User>(dataset.viewers);
  const initialEditorsFilter = FormDataFilter<User>(dataset.editors);
  const initialAdminsFilter = FormDataFilter<User>(dataset.admins);
  const initialProjectFilter = FindAndFormat<Project>(
    projects,
    dataset.projects.map((project) => project.id)
  );

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
    const response = await updateDatasetDetails(dataset.id, submittingData);
    if (response) {
      toast.error(`Update Dataset failed. Error: ${response.errorMessage}`);
    } else {
      toast.success("Update Dataset successful!");
    }
  };

  return (
    <Formik
      initialValues={{
        name: dataset.name,
        visibility: dataset.visibility, // Should be "PUBLIC" or "RESTRICTED"
        viewers: initialViewersFilter.map((viewer) => viewer.value),
        editors: initialEditorsFilter.map((editor) => editor.value),
        dataPartner: initialPartnerFilter[0].value,
        admins: initialAdminsFilter.map((admin) => admin.value),
        projects: initialProjectFilter.map((project) => project.value)
      }}
      onSubmit={(data) => {
        handleSubmit(data);
      }}
    >
      {({ values, handleChange, handleSubmit }) => (
        <form className="w-full max-w-2xl" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-5">

            <FormField name="name">
              {({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormDescription>
                    Name of the dataset.
                  </FormDescription>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder={dataset.name}
                      onChange={handleChange}
                      name="name"
                      disabled={!canUpdate}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            </FormField>

            <FormItem>
              <FormLabel>Data Partner</FormLabel>
              <FormDescription>
                The data partner that owns the dataset.
              </FormDescription>
              <FormControl>
                <FormikSelect
                  options={partnerOptions}
                  name="dataPartner"
                  placeholder="Choose an Data Partner"
                  isMulti={false}
                  isDisabled={!canUpdate}
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
                        defaultChecked={dataset.visibility === "PUBLIC" ? true : false}
                        disabled={!canUpdate}
                      />
                    </FormControl>
                    <span className="text-sm">
                      {/* Show user-friendly label */}
                      {values.visibility === "PUBLIC" ? "Shared" : "Restricted"}
                    </span>
                  </div>
                  <FormDescription>
                    If a Dataset is shared, then all users with access to any project associated to the Dataset can see them.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            </FormField>

            {!publicVisibility && (
              <FormItem>
                <FormLabel>Viewers</FormLabel>
                <FormDescription>
                  All Dataset admins and editors also have Dataset viewer permissions.
                </FormDescription>
                <FormControl>
                  <FormikSelect
                    options={userOptions}
                    name="viewers"
                    placeholder="Choose viewers"
                    isMulti={true}
                    isDisabled={!canUpdate}
                  />
                </FormControl>
              </FormItem>
            )}

            <FormItem>
              <FormLabel>Editors</FormLabel>
              <FormDescription>
                Dataset editors also have Scan Report editor permissions.
              </FormDescription>
              <FormControl>
                <FormikSelect
                  options={userOptions}
                  name="editors"
                  placeholder="Choose editors"
                  isMulti={true}
                  isDisabled={!canUpdate}
                />
              </FormControl>
            </FormItem>

            <FormItem>
              <FormLabel>Admins</FormLabel>
              <FormDescription>
                All Dataset admins also have Dataset editor permissions. Dataset admins also have Scan Report editor permissions.
              </FormDescription>
              <FormControl>
                <FormikSelect
                  options={userOptions}
                  name="admins"
                  placeholder="Choose admins"
                  isMulti={true}
                  isDisabled={!canUpdate}
                />
              </FormControl>
            </FormItem>

            <FormItem>
              <FormLabel>Projects</FormLabel>
              <FormDescription>
                The project that the dataset belongs to.
              </FormDescription>
              <FormControl>
                <FormikSelect
                  options={projectOptions}
                  name="projects"
                  placeholder="Choose projects"
                  isMulti={true}
                  isDisabled={!canUpdate}
                />
              </FormControl>
            </FormItem>

            <div className="flex mt-3">
              <Button
                type="submit"
                disabled={!canUpdate}
              >
                <Save />
                Save
              </Button>
            </div>
          </div>
        </form>
      )}
    </Formik>
  );
}

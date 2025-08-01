"use client";

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
import { updateScanReport } from "@/api/scanreports";

interface FormData {
  name: string;
  visibility: string;
  author: number;
  viewers: number[];
  editors: number[];
  parent_dataset: number;
}

export function ScanReportDetailsForm({
  datasetList,
  scanreport,
  users,
  permissions,
  isAuthor
}: {
  datasetList: DataSetSRList[];
  scanreport: ScanReport;
  users: User[];
  permissions: Permission[];
  isAuthor: boolean;
}) {
  // Permissions
  const canUpdate = permissions.includes("CanAdmin") || isAuthor;
  // State control for viewers fields
  const [publicVisibility, setPublicVisibility] = useState<boolean>(
    scanreport.visibility === "PUBLIC" ? true : false
  );

  // Making options suitable for React Select
  const userOptions = FormDataFilter<User>(users);
  const parentDatasetOptions = FormDataFilter<DataSetSRList>(datasetList);
  // Find the intial parent dataset and author which is required when adding Dataset
  const initialParentDataset = datasetList.find(
    (dataset) => scanreport.parent_dataset.name === dataset.name // parent's dataset is unique (set by the models.py) so can be used to find the initial parent dataset here
  )!;

  const initialAuthor = users.find((user) => scanreport.author.id === user.id)!;
  // Find and make initial data suitable for React select
  const initialDatasetFilter =
    FormDataFilter<DataSetSRList>(initialParentDataset);
  const initialAuthorFilter = FormDataFilter<User>(initialAuthor);
  const initialViewersFilter = FindAndFormat<User>(users, scanreport.viewers);
  const initialEditorsFilter = FindAndFormat<User>(users, scanreport.editors);

  const handleSubmit = async (data: FormData) => {
    const submittingData = {
      dataset: data.name,
      visibility: data.visibility,
      parent_dataset: data.parent_dataset,
      viewers: data.viewers || [],
      editors: data.editors || [],
      author: data.author
    };

    const response = await updateScanReport(
      scanreport.id,
      submittingData,
      true // "true" for the value "needRedirect"
    );
    if (response) {
      toast.error(`Update Scan Report failed. Error: ${response.errorMessage}`);
    } else {
      toast.success("Update Scan Report successful!");
    }
  };

  return (
    <Formik
      initialValues={{
        name: scanreport.dataset,
        visibility: scanreport.visibility,
        author: initialAuthorFilter[0].value,
        viewers: initialViewersFilter.map((viewer) => viewer.value),
        editors: initialEditorsFilter.map((editor) => editor.value),
        parent_dataset: initialDatasetFilter[0].value
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
                    Name of the Scan Report.
                  </FormDescription>
                  <FormControl>
                    <Input
                      {...field}
                      value={values.name}
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
              <FormLabel>Author</FormLabel>
              <FormDescription>
                Authors of a Scan Report can edit Scan Report details.
              </FormDescription>
              <FormControl>
                <FormikSelect
                  options={userOptions}
                  name="author"
                  placeholder="Choose an author"
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
                              value: checked ? "PUBLIC" : "RESTRICTED"
                            }
                          });
                          setPublicVisibility(checked);
                        }}
                        checked={values.visibility === "PUBLIC"}
                        disabled={!canUpdate}
                      />
                    </FormControl>
                    <span className="text-sm">
                      {/* Show user-friendly label */}
                      {values.visibility === "PUBLIC" ? "Shared" : "Restricted"}
                    </span>
                  </div>
                  <FormDescription>
                    To see the contents of the Scan Report, the Scan Report must be shared, or users must be an author/editor/viewer of the Scan Report.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            </FormField>

            {!publicVisibility && (
              <FormItem>
                <FormLabel>Viewers</FormLabel>
                <FormDescription>
                  Viewers of a Scan Report can perform read-only actions.
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
                Editors of a Scan Report can add/remove concepts, update tables and update fields.
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
              <FormLabel>Dataset</FormLabel>
              <FormDescription>
                The parent dataset of the Scan Report.
              </FormDescription>
              <FormControl>
                <FormikSelect
                  options={parentDatasetOptions}
                  name="parent_dataset"
                  placeholder="Choose a parent dataset"
                  isMulti={false}
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

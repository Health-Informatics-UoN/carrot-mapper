"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Save } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Form, Formik } from "formik";
import { toast } from "sonner";
import { FindAndFormat, FormDataFilter } from "../form-components/FormikUtils";
import { Tooltips } from "../core/Tooltips";
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
  isAuthor,
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
  const [sharedVisibility, setSharedVisibility] = useState<boolean>(
    scanreport.visibility === "SHARED" ? true : false
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
      author: data.author,
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
        parent_dataset: initialDatasetFilter[0].value,
      }}
      onSubmit={(data) => {
        handleSubmit(data);
      }}
    >
      {({ values, handleChange, handleSubmit }) => (
        <Form className="w-full" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-3 text-lg">
            <div className="flex items-center space-x-3">
              <h3 className="flex">
                {" "}
                Name
                <Tooltips content="Name of the Scan Report." />
              </h3>
              <Input
                value={values.name}
                onChange={handleChange}
                name="name"
                disabled={!canUpdate}
                className="text-lg"
              />
            </div>
            <div className="flex flex-col gap-2">
              <h3 className="flex">
                Author{" "}
                <Tooltips
                  content="Authors of a Scan Report can edit Scan Report details."
                  link="https://carrot4omop.ac.uk/Carrot-Mapper/projects-datasets-and-scanreports/#authors"
                />
              </h3>
              <FormikSelect
                options={userOptions}
                name="author"
                placeholder="Choose an author"
                isMulti={false}
                isDisabled={!canUpdate}
              />
            </div>
            <div className="flex items-center space-x-3">
              <h3 className="flex">
                Visibility
                <Tooltips
                  content="To see the contents of the Scan Report, the Scan Report must be SHARED, or users must be an author/editor/viewer of the Scan Report."
                  link="https://carrot4omop.ac.uk/Carrot-Mapper/projects-datasets-and-scanreports/#access-controls"
                />
              </h3>
              <Switch
                onCheckedChange={(checked) => {
                  handleChange({
                    target: {
                      name: "visibility",
                      value: checked ? "SHARED" : "RESTRICTED",
                    },
                  });
                  setSharedVisibility(checked);
                }}
                defaultChecked={
                  scanreport.visibility === "SHARED" ? true : false
                }
                disabled={!canUpdate}
              />
              <Label className="text-lg">
                {values.visibility === "SHARED" ? "SHARED" : "RESTRICTED"}
              </Label>
            </div>
            {!sharedVisibility && (
              <div className="flex flex-col gap-2">
                <h3 className="flex">
                  {" "}
                  Viewers
                  <Tooltips
                    content="Viewers of a Scan Report can perform read-only actions."
                    link="https://carrot4omop.ac.uk/Carrot-Mapper/projects-datasets-and-scanreports/#viewers"
                  />
                </h3>
                <FormikSelect
                  options={userOptions}
                  name="viewers"
                  placeholder="Choose viewers"
                  isMulti={true}
                  isDisabled={!canUpdate}
                />
              </div>
            )}
            <div className="flex flex-col gap-2">
              <h3 className="flex">
                {" "}
                Editors
                <Tooltips
                  content="Editors of a Scan Report can add/remove concepts, update tables and update fields."
                  link="https://carrot4omop.ac.uk/Carrot-Mapper/projects-datasets-and-scanreports/#editors"
                />
              </h3>
              <FormikSelect
                options={userOptions}
                name="editors"
                placeholder="Choose editors"
                isMulti={true}
                isDisabled={!canUpdate}
              />
            </div>
            <div className="flex flex-col gap-2">
              <h3 className="flex">
                {" "}
                Dataset
                <Tooltips content="The parent dataset of the Scan Report." />
              </h3>
              <FormikSelect
                options={parentDatasetOptions}
                name="parent_dataset"
                placeholder="Choose a parent dataset"
                isMulti={false}
                isDisabled={!canUpdate}
              />
            </div>
            <div className="flex mt-3">
              <Button
                type="submit"
                className="px-4 py-2 text-lg border border-input"
                disabled={!canUpdate}
              >
                Save <Save className="ml-2" />
              </Button>
              <Tooltips
                content="You must be the author of the scan report or an admin of the parent dataset
                    to update the details of this scan report."
              />
            </div>
          </div>
        </Form>
      )}
    </Formik>
  );
}

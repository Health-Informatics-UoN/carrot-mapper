"use client";
import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { updateScanReportTable } from "@/api/scanreports";
import { Check, Save, TriangleAlert, X } from "lucide-react";
import { toast } from "sonner";
import { FormDataFilter } from "../form-components/FormikUtils";
import { Form, Formik } from "formik";
import { Tooltips } from "../Tooltips";
import { FormikSelect } from "../form-components/FormikSelect";
import { Switch } from "../ui/switch";
import { Label } from "../ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";

interface FormData {
  personId: number | null;
  dateEvent: number | null;
  death_table: boolean;
}

export function ScanReportTableUpdateForm({
  scanreportFields,
  scanreportTable,
  permissions,
  personId,
  dateEvent,
}: {
  scanreportFields: ScanReportField[];
  scanreportTable: ScanReportTable;
  permissions: Permission[];
  personId: ScanReportField;
  dateEvent: ScanReportField;
}) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const canUpdate =
    permissions.includes("CanEdit") || permissions.includes("CanAdmin");

  const fieldOptions = FormDataFilter<ScanReportField>(scanreportFields);

  const initialPersonId = FormDataFilter<ScanReportField>(personId);
  const initialDateEvent = FormDataFilter<ScanReportField>(dateEvent);

  const handleSubmit = async (data: FormData) => {
    const submittingData = {
      person_id: data.personId !== 0 ? data.personId : null,
      date_event: data.dateEvent !== 0 ? data.dateEvent : null,
      death_table: data.death_table,
    };

    const response = await updateScanReportTable(
      scanreportTable.scan_report,
      scanreportTable.id,
      submittingData
    );
    if (response) {
      toast.error(
        `Update Scan Report Table failed. Error: ${response.errorMessage}`
      );
    } else {
      toast.success("Update Scan Report Table successful!");
    }
  };

  return (
    <Formik
      initialValues={{
        dateEvent: initialDateEvent[0].value,
        personId: initialPersonId[0].value,
        death_table: scanreportTable.death_table,
      }}
      onSubmit={(data) => {
        handleSubmit(data);
      }}
    >
      {({ handleSubmit, values, setFieldValue }) => (
        <Form className="w-full" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-3 text-lg">
            <div className="flex flex-col gap-2">
              <h3 className="flex">
                Person ID{" "}
                <Tooltips
                  content="Every CDM object must contain at least one person ID."
                  link="https://carrot4omop.ac.uk/Carrot-Mapper/mapping-rules/#1-person-id"
                />
              </h3>
              <FormikSelect
                options={fieldOptions}
                name="personId"
                placeholder="Choose a Person ID"
                isMulti={false}
                isDisabled={!canUpdate}
              />
            </div>

            <div className="flex flex-col gap-2">
              <h3 className="flex">
                {" "}
                Date Event
                <Tooltips
                  content="Every CDM object must contain at least one date_event."
                  link="https://carrot4omop.ac.uk/Carrot-Mapper/mapping-rules/#2-date-events"
                />
              </h3>
              <FormikSelect
                options={fieldOptions}
                name="dateEvent"
                placeholder="Choose a Date Event"
                isMulti={false}
                isDisabled={!canUpdate}
              />
            </div>

            <div className="flex gap-2 mt-2">
              <h3 className="flex">
                Does this table only contain data that need mapping to the DEATH
                table in OMOP CDM?
                <Tooltips content="If 'YES', concepts added here with domains RACE, ETHNICITY and GENDER will be mapped to the PERSON table. ALL of other concepts added here will be mapped to the DEATH table" />
              </h3>
              <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Please Confirm Your Choice</DialogTitle>
                    <DialogDescription>
                      Are you sure you want to set this table as a DEATH table?
                      Doing so will result in the following:
                      <ul className="text-gray-500 list-disc pl-4 pt-2">
                        <li>
                          Concepts added to this table with domains{" "}
                          <span className="font-bold">
                            RACE, ETHNICITY and GENDER
                          </span>{" "}
                          will be mapped to the{" "}
                          <span className="font-bold">PERSON</span> table in
                          OMOP CDM.
                        </li>
                        <li>
                          <span className="font-bold">
                            All concepts with other domains
                          </span>{" "}
                          will be mapped to the{" "}
                          <span className="font-bold">DEATH</span> table in OMOP
                          CDM.
                        </li>
                      </ul>
                      <h2 className="text-red-500 flex items-center">
                        <TriangleAlert className="size-4 mr-1 animate-pulse" />{" "}
                        <span className="underline underline-offset-2 mr-1">
                          Warning:
                        </span>{" "}
                        Once saved, this setting is permanent and cannot be
                        undone.{" "}
                      </h2>
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter className="flex gap-3">
                    <Button
                      onClick={() => {
                        setIsDialogOpen(false);
                      }}
                      variant={"outline"}
                    >
                      Cancel <X className="size-4 ml-2" />
                    </Button>
                    <Button
                      onClick={() => {
                        setFieldValue("death_table", true);
                        setIsDialogOpen(false);
                      }}
                    >
                      Confirm <Check className="size-4 ml-2" />
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
              <Switch
                checked={values.death_table}
                onCheckedChange={(checked) => {
                  if (checked) {
                    // When switching from NO to YES, show confirmation dialog
                    setIsDialogOpen(true);
                  } else {
                    // When switching from YES to NO, change immediately
                    setFieldValue("death_table", false);
                  }
                }}
                disabled={!canUpdate || scanreportTable.death_table}
              />
              <Label className="text-lg">
                {values.death_table === true ? "YES" : "NO"}
              </Label>
              {scanreportTable.death_table && (
                <Tooltips content="This setting is permanent, once set" />
              )}
            </div>

            <div className="flex mt-3">
              <Button
                type="submit"
                className="px-4 py-2 bg-carrot text-white rounded text-lg"
                disabled={!canUpdate}
              >
                Save <Save className="ml-2" />
              </Button>
              <Tooltips
                content="You must be the author of the scan report or an admin of the parent dataset
                    to update the details of this scan report table."
              />
            </div>
          </div>
        </Form>
      )}
    </Formik>
  );
}

"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { updateScanReportTable } from "@/api/scanreports";
import { Check, Save, X } from "lucide-react";
import { toast } from "sonner";
import { FormDataFilter } from "../form-components/FormikUtils";
import { Formik } from "formik";
import { FormField, FormItem, FormLabel, FormControl, FormMessage, FormDescription } from "@/components/ui/form";
import { FormikSelect } from "../form-components/FormikSelect";
import { useRouter } from "next/navigation";
import { Checkbox } from "../ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tooltips } from "@/components/core/Tooltips";
import { enableReuseTriggerOption } from "@/constants";

interface FormData {
  personId: number | null;
  dateEvent: number | null;
  triggerReuse: boolean;
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
  const router = useRouter();
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
      trigger_reuse: data.triggerReuse,
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
      router.push(`/scanreports/${scanreportTable.scan_report}/`);
    }
  };

  return (
    <Formik
      initialValues={{
        dateEvent: initialDateEvent[0].value,
        personId: initialPersonId[0].value,
        triggerReuse: scanreportTable.trigger_reuse,
        death_table: Boolean(scanreportTable.death_table),
      }}
      onSubmit={(data) => {
        handleSubmit(data);
      }}
    >
      {({ handleSubmit, values, setFieldValue }) => (
        <form className="w-full max-w-2xl" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-5">

            <FormItem>
              <FormLabel>Person ID</FormLabel>
              <FormDescription>
                Every CDM object must contain at least one person ID.
              </FormDescription>
              <FormControl>
                <FormikSelect
                  options={fieldOptions}
                  name="personId"
                  placeholder="Choose a Person ID"
                  isMulti={false}
                  isDisabled={!canUpdate}
                />
              </FormControl>
            </FormItem>

            <FormItem>
              <FormLabel>Date Event</FormLabel>
              <FormDescription>
                Every CDM object must contain at least one date_event.
              </FormDescription>
              <FormControl>
                <FormikSelect
                  options={fieldOptions}
                  name="dateEvent"
                  placeholder="Choose a Date Event"
                  isMulti={false}
                  isDisabled={!canUpdate}
                />
              </FormControl>
            </FormItem>

            <FormItem>
              <div className="flex flex-wrap items-center gap-2">
                <FormLabel className="mb-0">
                  Does this table contain only death data for the OMOP CDM Death
                  table?
                </FormLabel>
                <Tooltips
                  content="In the Carrot data standard, death data is provided in a separate file (e.g. death.csv). Mark Yes if this table contains that death data to be mapped to the OMOP Death table."
                />
                <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Please Confirm Your Choice</DialogTitle>
                      <DialogDescription>
                        Are you sure you want to set this table as a Death table?
                        Doing so will result in the following:
                        <ul className="text-gray-500 list-disc pl-4 py-2">
                          <li>
                            Mapping Rules that are created either manually or
                            automatically (built from OMOP vocabulary or Reused)
                            will have Destination table as{" "}
                            <span className="font-bold">Death</span>.
                          </li>
                          <li>
                            All concepts in this table will be recognised as{" "}
                            <span className="font-bold">Cause of Death</span> in
                            OMOP CDM.
                          </li>
                          <li>
                            Destination of Date Event will be{" "}
                            <span className="font-bold">Death date</span> field in
                            OMOP CDM.
                          </li>
                        </ul>
                        <p className="text-muted-foreground text-pretty">
                          You can turn off this setting later. Mapping rules will
                          be refreshed when you save.
                        </p>
                      </DialogDescription>
                    </DialogHeader>
                    <DialogFooter className="flex gap-3">
                      <Button
                        type="button"
                        onClick={() => setIsDialogOpen(false)}
                        variant="outline"
                      >
                        Cancel <X className="size-4 ml-2" />
                      </Button>
                      <Button
                        type="button"
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
                      setIsDialogOpen(true);
                    } else {
                      setFieldValue("death_table", false);
                    }
                  }}
                  disabled={!canUpdate}
                />
                <Label className="text-lg">
                  {values.death_table === true ? "YES" : "NO"}
                </Label>
              </div>
            </FormItem>

            {enableReuseTriggerOption === "true" && (
              <FormField name="triggerReuse">
                {({ field }) => (
                  <FormItem>
                    <div className="flex gap-2 items-center">
                      <FormLabel>Do you want to trigger the reuse of existing concepts?</FormLabel>
                      <FormControl>
                        <Checkbox
                          checked={values.triggerReuse}
                          onCheckedChange={(checked) => {
                            setFieldValue("triggerReuse", checked);
                          }}
                          disabled={!canUpdate}
                          className="size-5"
                        />
                      </FormControl>
                      <span className="text-sm">
                        {values.triggerReuse === true ? "Yes" : "No"}
                      </span>
                    </div>
                    <FormDescription>
                      If Yes, concepts added to other scan reports which are in same parent dataset will be reused, based on the matching value and field. This feature may make the auto mapping process longer to run.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              </FormField>
            )}

            <div className="flex mt-3">
              <Button
                type="submit"
                disabled={!canUpdate}
              >
                <Save className="h-4 w-4" />
                Save
              </Button>
            </div>
          </div>
        </form>
      )}
    </Formik>
  );
}

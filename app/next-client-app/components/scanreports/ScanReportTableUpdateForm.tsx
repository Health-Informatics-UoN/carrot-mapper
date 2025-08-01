"use client";

import { Button } from "@/components/ui/button";
import { updateScanReportTable } from "@/api/scanreports";
import { Save } from "lucide-react";
import { toast } from "sonner";
import { FormDataFilter } from "../form-components/FormikUtils";
import { Formik } from "formik";
import { FormField, FormItem, FormLabel, FormControl, FormMessage, FormDescription } from "@/components/ui/form";
import { FormikSelect } from "../form-components/FormikSelect";
import { useRouter } from "next/navigation";
import { Checkbox } from "../ui/checkbox";
import { enableReuseTriggerOption } from "@/constants";

interface FormData {
  personId: number | null;
  dateEvent: number | null;
  triggerReuse: boolean;
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
                        {values.triggerReuse === true ? "YES" : "NO"}
                      </span>
                    </div>
                    <FormDescription>
                      If YES, concepts added to other scan reports which are in same parent dataset will be reused, based on the matching value and field. This feature may make the auto mapping process longer to run.
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

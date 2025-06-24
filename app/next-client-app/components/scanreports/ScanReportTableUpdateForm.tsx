"use client";

import { Button } from "@/components/ui/button";
import { updateScanReportTable } from "@/api/scanreports";
import { Save } from "lucide-react";
import { toast } from "sonner";
import { FormDataFilter } from "../form-components/FormikUtils";
import { Form, Formik } from "formik";
import { FormikSelect } from "../form-components/FormikSelect";
import { Label } from "../ui/label";
import { Tooltips } from "../core/Tooltips";
import { useRouter } from "next/navigation";
import { Checkbox } from "../ui/checkbox";
import { env } from "next-runtime-env";

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
  const NEXT_PUBLIC_ENABLE_REUSE_TRIGGER_OPTION = env(
    "NEXT_PUBLIC_ENABLE_REUSE_TRIGGER_OPTION"
  );
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
            {NEXT_PUBLIC_ENABLE_REUSE_TRIGGER_OPTION === "true" && (
              <div className="flex gap-2 mt-2 items-center">
                <h3 className="flex">
                  Do you want to trigger the reuse of existing concepts?
                  <Tooltips
                    content="If YES, concepts added to other scan reports which are in same
                      parent dataset will be reused, based
                      on the matching value and field. This feature may make the
                      auto mapping process longer to run."
                  />
                </h3>
                <Checkbox
                  checked={values.triggerReuse}
                  onCheckedChange={(checked) => {
                    setFieldValue("triggerReuse", checked);
                  }}
                  disabled={!canUpdate}
                  className="size-5"
                />
                <Label className="text-lg">
                  {values.triggerReuse === true ? "YES" : "NO"}
                </Label>
              </div>
            )}
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

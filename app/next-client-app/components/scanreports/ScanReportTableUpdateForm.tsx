"use client";

import { Button } from "@/components/ui/button";
import { updateScanReportTable } from "@/api/scanreports";
import { Save } from "lucide-react";
import { toast } from "sonner";
import { FormDataFilter } from "../form-components/FormikUtils";
import { Formik } from "formik";
import {
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { FormikSelect } from "../form-components/FormikSelect";
import { useRouter } from "next/navigation";
import { Checkbox } from "../ui/checkbox";
import { enableReuseTriggerOption } from "@/constants";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ConceptIdInput } from "./ConceptIdInput";

interface FormData {
  personId: number | null;
  dateEvent: number | null;
  triggerReuse: boolean;
  tableRole: TableRole;
  typeConcept: string;
}

const TABLE_ROLES: { value: TableRole; label: string; description: string }[] =
  [
    {
      value: "standard",
      label: "Standard",
      description:
        "Concepts are mapped to the OMOP table their domain points to, e.g. Condition concepts to condition_occurrence.",
    },
    {
      value: "death",
      label: "Death",
      description:
        "Mapping rules for this table will have Destination table as Death, concepts will be recognised as Cause of Death, and the Date Event will map to the Death date field in OMOP CDM.",
    },
  ];

export function ScanReportTableUpdateForm({
  scanreportFields,
  scanreportTable,
  permissions,
  personId,
  dateEvent,
  typeConceptName,
}: {
  scanreportFields: ScanReportField[];
  scanreportTable: ScanReportTable;
  permissions: Permission[];
  personId: ScanReportField;
  dateEvent: ScanReportField;
  typeConceptName: string | null;
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
      table_role: data.tableRole,
      type_concept: data.typeConcept ? Number(data.typeConcept) : null,
    };
    if (data.typeConcept && !/^\d+$/.test(data.typeConcept)) {
      toast.error("The type concept must be a concept ID (a number).");
      return;
    }

    const response = await updateScanReportTable(
      scanreportTable.scan_report,
      scanreportTable.id,
      submittingData,
    );
    if (response) {
      toast.error(
        `Update Scan Report Table failed. Error: ${response.errorMessage}`,
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
        tableRole: scanreportTable.table_role,
        typeConcept: scanreportTable.type_concept?.toString() ?? "",
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
              <FormLabel htmlFor="tableRole">Table role</FormLabel>
              <FormDescription>
                What this table&apos;s rows become in the OMOP CDM.
              </FormDescription>
              <FormControl>
                <Select
                  value={values.tableRole}
                  onValueChange={(role) => setFieldValue("tableRole", role)}
                  disabled={!canUpdate}
                >
                  <SelectTrigger id="tableRole" className="max-w-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TABLE_ROLES.map((role) => (
                      <SelectItem key={role.value} value={role.value}>
                        {role.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormControl>
              <FormDescription>
                {
                  TABLE_ROLES.find((role) => role.value === values.tableRole)
                    ?.description
                }
              </FormDescription>
            </FormItem>

            <FormItem>
              <FormLabel htmlFor="typeConcept">Type concept</FormLabel>
              <FormDescription>
                Optional. Records the provenance of every record built from this
                table in its *_type_concept_id field, e.g. 32817 (EHR). Check
                the ID in your vocabulary.
              </FormDescription>
              <FormControl>
                <ConceptIdInput
                  id="typeConcept"
                  value={values.typeConcept}
                  initialName={typeConceptName}
                  onChange={(value) => setFieldValue("typeConcept", value)}
                  disabled={!canUpdate}
                />
              </FormControl>
            </FormItem>

            {enableReuseTriggerOption === "true" && (
              <FormField name="triggerReuse">
                {({ field }) => (
                  <FormItem>
                    <div className="flex gap-2 items-center">
                      <FormLabel>
                        Do you want to trigger the reuse of existing concepts?
                      </FormLabel>
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
                      If Yes, concepts added to other scan reports which are in
                      same parent dataset will be reused, based on the matching
                      value and field. This feature may make the auto mapping
                      process longer to run.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              </FormField>
            )}

            <div className="flex mt-3">
              <Button type="submit" disabled={!canUpdate}>
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

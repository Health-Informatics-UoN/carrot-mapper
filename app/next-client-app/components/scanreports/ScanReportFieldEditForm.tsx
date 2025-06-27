"use client";

import { Button } from "@/components/ui/button";
import { Save } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Form, Formik } from "formik";
import { Tooltips } from "../core/Tooltips";
import { Checkbox } from "../ui/checkbox";
import { Textarea } from "../ui/textarea";
import { updateScanReportField } from "@/api/scanreports";
import { toast } from "sonner";

interface FormData {
  description: string | null;
  isIgnore: boolean;
  fromSource: boolean;
}

export function ScanReportFieldEditForm({
  scanReportField,
  permissions,
  scanreportId,
}: {
  scanReportField: ScanReportField | null;
  permissions: Permission[];
  scanreportId: number;
}) {
  if (scanReportField) {
    // Permissions
    const canUpdate =
      permissions.includes("CanEdit") || permissions.includes("CanAdmin");

    const handleSubmit = async (data: FormData) => {
      const submittingData = {
        pass_from_source: data.fromSource,
        is_ignore: data.isIgnore,
        description_column: data.description,
      };

      const response = await updateScanReportField(
        scanreportId,
        scanReportField.scan_report_table,
        scanReportField?.id.toString(),
        submittingData
      );
      if (response) {
        toast.error(`Update Field failed. Error: ${response.errorMessage}`);
      } else {
        toast.success("Update Field successful!");
        // If the redirect is used in API endpoint, the link to edit field page will be broken after succesful update
        // This can be fixed by adding the SR id to the data of the table, but it's taking more code than the below solution
        setTimeout(() => {
          window.location.href = `/scanreports/${scanreportId}/tables/${scanReportField?.scan_report_table}/`;
        }, 200); // Delay the redirection for a bit to make sure the toast is showing
      }
    };

    return (
      <Formik
        initialValues={{
          fromSource: scanReportField.pass_from_source,
          isIgnore: scanReportField.is_ignore,
          description: scanReportField.description_column,
        }}
        onSubmit={(data) => {
          handleSubmit(data);
        }}
      >
        {({ values, handleChange, handleSubmit }) => (
          <Form className="w-full" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-3 text-lg">
              <div className="flex items-center space-x-3">
                <Checkbox
                  onCheckedChange={(checked) => {
                    handleChange({
                      target: {
                        name: "isIgnore",
                        value: checked ? true : false,
                      },
                    });
                  }}
                  defaultChecked={scanReportField?.is_ignore}
                  disabled={!canUpdate}
                />
                <Label className="text-lg">Is ignore</Label>
              </div>
              <div className="flex items-center space-x-3">
                <Checkbox
                  onCheckedChange={(checked) => {
                    handleChange({
                      target: {
                        name: "fromSource",
                        value: checked ? true : false,
                      },
                    });
                  }}
                  defaultChecked={scanReportField?.pass_from_source}
                  disabled={!canUpdate}
                />
                <Label className="text-lg">Pass from source</Label>
              </div>
              <div className="flex flex-col gap-2">
                <h3>Description Column</h3>
                <Textarea
                  name="description"
                  onChange={handleChange}
                  value={values.description}
                  placeholder={scanReportField.description_column}
                />
              </div>
              <div>
                <Button
                  type="submit"
                  className="px-4 py-2 mt-3 text-lg"
                  disabled={!canUpdate}
                >
                  Save <Save className="ml-2" />
                </Button>
              </div>
            </div>
          </Form>
        )}
      </Formik>
    );
  }
}

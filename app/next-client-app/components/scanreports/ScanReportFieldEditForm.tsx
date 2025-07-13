"use client";

import { Button } from "@/components/ui/button";
import { Save } from "lucide-react";
import { FormField, FormItem, FormLabel, FormControl, FormMessage, FormDescription } from "@/components/ui/form";
import { Formik } from "formik";
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
          <form className="w-full max-w-2xl" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-3">

              <FormField name="isIgnore">
                {({ field }) => (
                  <FormItem>
                    <div className="flex items-center space-x-3">
                      <FormControl>
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
                      </FormControl>
                      <FormLabel>Is ignore</FormLabel>
                    </div>
                    <FormDescription>
                      When checked, this field will be ignored during the mapping process.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              </FormField>

              <FormField name="fromSource">
                {({ field }) => (
                  <FormItem>
                    <div className="flex items-center space-x-3">
                      <FormControl>
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
                      </FormControl>
                      <FormLabel>Pass from source</FormLabel>
                    </div>
                    <FormDescription>
                      When checked, this field will be passed through from the source data without modification.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              </FormField>

              <FormField name="description">
                {({ field }) => (
                  <FormItem>
                    <FormLabel>Description Column</FormLabel>
                    <FormDescription>
                      Additional description or notes for this field.
                    </FormDescription>
                    <FormControl>
                      <Textarea
                        {...field}
                        name="description"
                        onChange={handleChange}
                        value={values.description}
                        placeholder={scanReportField.description_column}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              </FormField>

              <div>
                <Button
                  type="submit"
                  disabled={!canUpdate}
                >
                  Save <Save className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          </form>
        )}
      </Formik>
    );
  }
}

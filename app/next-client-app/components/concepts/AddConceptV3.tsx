import {
    addConceptV3,
  } from "@/api/concepts";
  import { Button } from "@/components/ui/button";
  import { Input } from "@/components/ui/input";
  import { Form, Formik } from "formik";
  import { toast } from "sonner";
  
  interface AddConceptProps {
    rowId: number;
    tableId: string;
    contentType: "scanreportvalue" | "scanreportfield";
    disabled: boolean;
    scanReportId: string;
    fieldId: string;
  }
  
  export default function AddConceptV3({
    rowId,
    tableId,
    contentType,
    disabled,
    scanReportId,
    fieldId,
  }: AddConceptProps) {
    const handleSubmit = async (conceptCode: number) => {
      try {
        const response = await addConceptV3({
          concept: conceptCode,
          object_id: rowId,
          content_type: contentType,
          creation_type: "M",
          table_id: tableId,
        }, `/scanreports/${scanReportId}/tables/${tableId}/fields/${fieldId}/beta`);
  
        if (response) {
          toast.error(`Adding concept failed. ${response.errorMessage}`);
        } else {
          toast.success(`OMOP Concept successfully added.`);
        }
      } catch (error) {
        toast.error(`Adding concept failed. Error: Unknown error`);
      }
    };
  
    return (
      <Formik
        initialValues={{ concept: "" }}
        onSubmit={(data, actions) => {
          handleSubmit(Number(data.concept));
          actions.resetForm();
        }}
      >
        {({ values, handleChange, handleSubmit }) => (
          <Form onSubmit={handleSubmit}>
            <div className="flex gap-2">
              <div>
                <Input
                  type="text"
                  name="concept"
                  value={values.concept}
                  onChange={handleChange}
                  required
                  className="w-[180px]"
                  pattern="\d*"
                />
              </div>
              <Button type="submit" disabled={disabled}>
                Add
              </Button>
            </div>
          </Form>
        )}
      </Formik>
    );
  }
  
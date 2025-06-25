import {
  addConcept,
  getAllConceptsFiltered,
  getAllScanReportConcepts
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
  addSR: (concept: ScanReportConcept, c: Concept) => void;
}

export default function AddConcept({
  rowId,
  tableId,
  contentType,
  disabled,
  addSR
}: AddConceptProps) {
  const handleSubmit = async (conceptCode: number) => {
    try {
      const response = await addConcept({
        concept: conceptCode,
        object_id: rowId,
        content_type: contentType,
        creation_type: "M",
        table_id: tableId
      });

      if (response) {
        toast.error(`Adding concept failed. ${response.errorMessage}`);
      } else {
        const newConcepts = await getAllScanReportConcepts(
          `object_id=${rowId}`
        );
        const filteredConcepts = await getAllConceptsFiltered(
          newConcepts?.map((item) => item.concept).join(",")
        );
        // Filter the concept and concept filter
        const newConcept = newConcepts.filter(
          (c) => c.concept == conceptCode
        )[0];
        const filteredConcept = filteredConcepts.filter(
          (c) => c.concept_id == conceptCode
        )[0];

        addSR(newConcept, filteredConcept);
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
            <Button
              type="submit"
              disabled={disabled}
              className="bg-primary text-primary-foreground dark:bg-[hsl(var(--secondary))] dark:text-white hover:bg-gray-300 dark:hover:bg-gray-700"
            >
              Add
            </Button>
          </div>
        </Form>
      )}
    </Formik>
  );
}

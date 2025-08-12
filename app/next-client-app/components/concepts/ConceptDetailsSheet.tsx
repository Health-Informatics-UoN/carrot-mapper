import React, { useEffect, useState, useMemo } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import {
  getScanReportConceptDetail,
  updateScanReportConceptDetail,
} from "@/api/concepts";
import { InfoItem } from "@/components/core/InfoItem";
import { Formik } from "formik";
import {
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Save } from "lucide-react";
import { toast } from "sonner";

interface ConceptDetailsSheetProps {
  concept: ScanReportConceptV3;
  children: React.ReactNode;
  scanReportId?: string;
  tableId?: string;
  fieldId?: string;
  valueId?: number;
}

const getCreationTypeDescription = (creationType: string) => {
  switch (creationType) {
    case "V":
      return "Built from a OMOP vocabulary";
    case "M":
      return "Added manually";
    case "R":
      return "Added through mapping reuse";
    default:
      return "";
  }
};

const CONCEPT_DETAIL_FIELDS = [
  { label: "Concept ID", key: "concept_id" },
  { label: "Concept Name", key: "concept_name" },
  { label: "Concept Code", key: "concept_code" },
  { label: "Domain", key: "domain_id" },
  { label: "Vocabulary", key: "vocabulary_id" },
  { label: "Concept Class", key: "concept_class_id" },
  { label: "Standard Concept", key: "standard_concept" },
  { label: "Valid Start Date", key: "valid_start_date" },
  { label: "Valid End Date", key: "valid_end_date" },
  { label: "Invalid Reason", key: "invalid_reason" },
] as const;

interface FormData {
  description: string;
  confidence: number;
}

interface ConceptEditFormProps {
  conceptDetail: ScanReportConceptDetailV3;
  scanReportId: string;
  tableId: string;
  fieldId: string;
  valueId: number;
  conceptId: number;
  onUpdate: (updatedDetail: ScanReportConceptDetailV3) => void;
}

function ConceptEditForm({
  conceptDetail,
  scanReportId,
  tableId,
  fieldId,
  valueId,
  conceptId,
  onUpdate,
}: ConceptEditFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleUpdateConcept = async (data: FormData) => {
    setIsSubmitting(true);
    try {
      const response = await updateScanReportConceptDetail(
        scanReportId,
        tableId,
        fieldId,
        valueId.toString(),
        conceptId.toString(),
        {
          description: data.description,
          confidence: data.confidence,
        }
      );

      if (response) {
        onUpdate(response);
        toast.success("Concept details updated");
      }
    } catch (error: any) {
      toast.error(`Update failed. Error: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Formik
      initialValues={{
        description: conceptDetail.description || "",
        confidence:
          typeof conceptDetail.confidence === "number"
            ? conceptDetail.confidence
            : parseFloat(conceptDetail.confidence) || 0,
      }}
      onSubmit={handleUpdateConcept}
    >
      {({ values, handleChange, handleSubmit, setFieldValue }) => (
        <form onSubmit={handleSubmit}>
          <FormField name="confidence">
            {({ field }) => (
              <FormItem>
                <FormLabel>Confidence</FormLabel>
                <FormDescription>
                  Confidence score for the mapping (0.00 - 1.00)
                </FormDescription>
                <FormControl>
                  <div className="space-y-2">
                    <Slider
                      min={0}
                      max={100}
                      step={1}
                      value={[Math.round(values.confidence * 100)]}
                      onValueChange={(value) => {
                        setFieldValue("confidence", value[0] / 100);
                      }}
                      className="w-full"
                    />
                    <div className="text-sm text-muted-foreground">
                      Current value:{" "}
                      {(typeof values.confidence === "number"
                        ? values.confidence
                        : parseFloat(values.confidence) || 0
                      ).toFixed(2)}
                    </div>
                  </div>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          </FormField>
          <div className="mt-4">
            <FormField name="description">
              {({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormDescription>
                    Description of the concept mapping.
                  </FormDescription>
                  <FormControl>
                    <Textarea
                      {...field}
                      placeholder="Enter description"
                      onChange={handleChange}
                      name="description"
                      rows={3}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            </FormField>
          </div>
          <div className="flex mt-4">
            <Button type="submit" size="sm" disabled={isSubmitting}>
              <Save className="mr-2 h-4 w-4" />
              {isSubmitting ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </form>
      )}
    </Formik>
  );
}

export function ConceptDetailsSheet({
  concept,
  children,
  scanReportId,
  tableId,
  fieldId,
  valueId,
}: ConceptDetailsSheetProps) {
  const [conceptDetail, setConceptDetail] =
    useState<ScanReportConceptDetailV3 | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const handleUpdateConcept = useMemo(() => (updatedDetail: ScanReportConceptDetailV3) => {
    setConceptDetail(updatedDetail);
  }, []);

  useEffect(() => {
    if (isOpen && scanReportId && tableId && fieldId) {
      const fetchConceptDetail = async () => {
        setIsLoading(true);
        setError(null);
        try {
          const detail = await getScanReportConceptDetail(
            scanReportId,
            tableId,
            fieldId,
            valueId?.toString() || "",
            concept.id.toString()
          );
          setConceptDetail(detail);
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : "Failed to fetch concept detail";
          setError(errorMessage);
          console.error("Failed to fetch concept detail:", error);
        } finally {
          setIsLoading(false);
        }
      };

      fetchConceptDetail();
    }
  }, [isOpen, scanReportId, tableId, fieldId, valueId, concept.id]);

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>{children}</SheetTrigger>
      <SheetContent className="flex flex-col h-full">
        <SheetHeader className="flex-shrink-0">
          <SheetTitle>
            {concept.concept.concept_id} - {concept.concept.concept_name}
          </SheetTitle>
        </SheetHeader>
        <div className="space-y-6 flex-1 overflow-y-auto px-1">
          <div>
            <h3 className="font-semibold text-lg">Mapping Details</h3>
            <div className="space-y-3 text-sm py-4">
              <div>
                <InfoItem
                  label="Creation Type"
                  value={getCreationTypeDescription(concept.creation_type)}
                />
              </div>

              {isLoading && (
                <div className="text-muted-foreground py-2">
                  Loading additional details...
                </div>
              )}

              {error && (
                <div className="text-red-600 py-2">
                  Error: {error}
                </div>
              )}

              {conceptDetail && !isLoading && (
                <>
                  <div className="space-y-3">
                    <div>
                      <InfoItem
                        label="Created At"
                        value={new Date(
                          conceptDetail.created_at
                        ).toLocaleString()}
                      />
                    </div>
                    <div>
                      <InfoItem
                        label="Created By"
                        value={conceptDetail.created_by?.username || "Unknown"}
                      />
                    </div>
                    <div>
                      <InfoItem
                        label="Mapping Tool"
                        value={conceptDetail.mapping_tool}
                      />
                    </div>
                    <div>
                      <InfoItem
                        label="Mapping Tool Version"
                        value={conceptDetail.mapping_tool_version}
                      />
                    </div>
                  </div>

                  <div className="pt-4 border-t">
                    <ConceptEditForm
                      conceptDetail={conceptDetail}
                      scanReportId={scanReportId!}
                      tableId={tableId!}
                      fieldId={fieldId!}
                      valueId={valueId!}
                      conceptId={concept.id}
                      onUpdate={handleUpdateConcept}
                    />
                  </div>

                  <hr className="my-6" />
                  <h3 className="font-semibold mb-4 text-lg">
                    Concept Details
                  </h3>
                  <div className="space-y-3 text-sm">
                    {CONCEPT_DETAIL_FIELDS.map((field) => (
                      <div key={field.key}>
                        <InfoItem
                          label={field.label}
                          value={conceptDetail.concept[field.key]}
                        />
                      </div>
                    ))}
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    asChild
                  >
                    <a
                      href={`https://athena.ohdsi.org/search-terms/terms/${conceptDetail.concept.concept_id}`}
                      target="_blank"
                    >
                      View on Athena
                    </a>
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

import React, { useEffect, useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { getScanReportConceptDetail, updateScanReportConceptDetail } from "@/api/concepts";
import { InfoItem } from "@/components/core/InfoItem";
import { Formik } from "formik";
import { FormField, FormItem, FormLabel, FormControl, FormMessage, FormDescription } from "@/components/ui/form";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Save } from "lucide-react";
import { toast } from "sonner";

interface ConceptDetailsSheetProps {
  concept: any; // Using any for now since we don't have the exact type
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
  onUpdate 
}: ConceptEditFormProps) {
  const handleUpdateConcept = async (data: FormData) => {
    try {
      const response = await updateScanReportConceptDetail(
        scanReportId,
        tableId,
        fieldId,
        valueId.toString(),
        conceptId.toString(),
        { 
          description: data.description,
          confidence: data.confidence
        }
      );
      
      if (response) {
        onUpdate(response);
        toast.success("Concept details updated");
      }
    } catch (error: any) {
      toast.error(`Update failed. Error: ${error.message}`);
    }
  };

  return (
    <Formik
      initialValues={{
        description: conceptDetail.description || "",
        confidence: typeof conceptDetail.confidence === 'number' ? conceptDetail.confidence : parseFloat(conceptDetail.confidence) || 0
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
                        Current value: {(typeof values.confidence === 'number' ? values.confidence : parseFloat(values.confidence) || 0).toFixed(2)}
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
            <Button
              type="submit"
              size="sm"
            >
              <Save className="mr-2 h-4 w-4" />
              Save Changes
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
  valueId
}: ConceptDetailsSheetProps) {
  const [conceptDetail, setConceptDetail] = useState<ScanReportConceptDetailV3 | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const handleUpdateConcept = (updatedDetail: ScanReportConceptDetailV3) => {
    setConceptDetail(updatedDetail);
  };

  useEffect(() => {
    if (isOpen && scanReportId && tableId && fieldId) {
      const fetchConceptDetail = async () => {
        setIsLoading(true);
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
          console.error("Failed to fetch concept detail:", error);
        } finally {
          setIsLoading(false);
        }
      };

      fetchConceptDetail();
    }
  }, [isOpen, scanReportId, tableId, fieldId, concept.id]);

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        {children}
      </SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>
            {concept.concept.concept_id} - {concept.concept.concept_name}
          </SheetTitle>
        </SheetHeader>
        <div className="mt-6 space-y-6">
          <div>
            <h3 className="font-semibold mb-4 text-lg">Mapping Details</h3>
            <div className="space-y-3 text-sm py-4">
              <div>
                <InfoItem
                  label="Concept ID"
                  value={concept.concept.concept_id}
                />
              </div>
              <div>
                <InfoItem
                  label="Concept Name"
                  value={concept.concept.concept_name}
                />
              </div>
              <div>
                <InfoItem
                  label="Concept Code"
                  value={concept.concept.concept_code}
                />
              </div>
              <div>
                <InfoItem
                  label="Creation Type"
                  value={getCreationTypeDescription(concept.creation_type)}
                />
              </div>
              
              {isLoading && (
                <div className="text-muted-foreground py-2">Loading additional details...</div>
              )}
              
              {conceptDetail && !isLoading && (
                <>
                  <div className="space-y-3 pt-2 border-t">
                    <div>
                      <InfoItem
                        label="Created At"
                        value={new Date(conceptDetail.created_at).toLocaleString()}
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
                  <h3 className="font-semibold mb-4 text-lg">Concept Details</h3>
                  <div className="space-y-3 text-sm">
                    <div>
                      <InfoItem
                        label="Concept"
                        value={conceptDetail.concept.concept_id}
                      />
                    </div>
                    <div>
                      <InfoItem
                        label="Domain"
                        value={conceptDetail.concept.domain_id}
                      />
                    </div>
                    <div>
                      <InfoItem
                        label="Vocabulary"
                        value={conceptDetail.concept.vocabulary_id}
                      />
                    </div>
                    <div>
                      <InfoItem
                        label="Concept Class"
                        value={conceptDetail.concept.concept_class_id}
                      />
                    </div>
                    <div>
                      <InfoItem
                        label="Standard Concept"
                        value={conceptDetail.concept.standard_concept}
                      />
                    </div>
                    <div>
                      <InfoItem
                        label="Valid Start Date"
                        value={conceptDetail.concept.valid_start_date}
                        />
                    </div>
                    <div>
                      <InfoItem
                        label="Valid End Date"
                        value={conceptDetail.concept.valid_end_date}
                        />
                    </div>
                    <div>
                      <InfoItem
                        label="Invalid Reason"
                        value={conceptDetail.concept.invalid_reason}
                      />
                    </div>
                  </div>
                  
                <Button variant="outline" size="sm" className="w-full" asChild>
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

import React, { useEffect, useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Cross2Icon } from "@radix-ui/react-icons";
import { getScanReportConceptDetail } from "@/api/concepts";

interface ConceptDetailsSheetProps {
  concept: any; // Using any for now since we don't have the exact type
  children: React.ReactNode;
  onDelete?: (conceptId: number) => Promise<void>;
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

export function ConceptDetailsSheet({ 
  concept, 
  children, 
  onDelete,
  scanReportId,
  tableId,
  fieldId,
  valueId
}: ConceptDetailsSheetProps) {
  const [conceptDetail, setConceptDetail] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onDelete) {
      await onDelete(concept.id);
    }
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
          <SheetDescription>
            {getCreationTypeDescription(concept.creation_type)}
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-4">
          <div>
            <h3 className="font-semibold mb-2">Concept Details</h3>
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-medium">Concept ID:</span> {concept.concept.concept_id}
              </div>
              <div>
                <span className="font-medium">Concept Name:</span> {concept.concept.concept_name}
              </div>
              <div>
                <span className="font-medium">Concept Code:</span> {concept.concept.concept_code}
              </div>
              <div>
                <span className="font-medium">Creation Type:</span> {concept.creation_type}
              </div>
              {isLoading && (
                <div className="text-muted-foreground">Loading additional details...</div>
              )}
              {conceptDetail && !isLoading && (
                <>
                  <div>
                    <span className="font-medium">Created At:</span> {new Date(conceptDetail.created_at).toLocaleString()}
                  </div>
                  <div>
                    <span className="font-medium">Created By:</span> {conceptDetail.created_by?.username || "Unknown"}
                  </div>
                  <div>
                    <span className="font-medium">Confidence:</span> {conceptDetail.confidence}
                  </div>
                  <div>
                    <span className="font-medium">Description:</span> {conceptDetail.description}
                  </div>
                  <div>
                    <span className="font-medium">Mapping Tool:</span> {conceptDetail.mapping_tool}
                  </div>
                  <div>
                    <span className="font-medium">Mapping Tool Version:</span> {conceptDetail.mapping_tool_version}
                  </div>
                  <div>
                    <span className="font-medium">Concept:</span> {conceptDetail.concept.concept_id} - {conceptDetail.concept.concept_name} - {conceptDetail.concept.concept_code}
                  </div>
                  <div>
                    <span className="font-medium">Domain:</span> {conceptDetail.concept.domain_id}
                  </div>
                  <div>
                    <span className="font-medium">Vocabulary:</span> {conceptDetail.concept.vocabulary_id}
                  </div>
                  <div>
                    <span className="font-medium">Concept Class:</span> {conceptDetail.concept.concept_class_id}
                  </div>
                  <div>
                    <span className="font-medium">Standard Concept:</span> {conceptDetail.concept.standard_concept}
                  </div>
                  <div>
                    <span className="font-medium">Valid Start Date:</span> {conceptDetail.concept.valid_start_date}
                  </div>
                  <div>
                    <span className="font-medium">Valid End Date:</span> {conceptDetail.concept.valid_end_date}
                  </div>
                  <div>
                    <span className="font-medium">Invalid Reason:</span> {conceptDetail.concept.invalid_reason}
                  </div>
                  
                </>
              )}
            </div>
          </div>
          {onDelete && (
            <div className="pt-4 border-t">
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDelete}
                className="w-full"
              >
                <Cross2Icon className="mr-2 h-4 w-4" />
                Delete Concept
              </Button>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
} 
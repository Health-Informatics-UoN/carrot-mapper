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
import { InfoItem } from "@/components/core/InfoItem";

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
        </SheetHeader>
        <div className="mt-6 space-y-4">
          <div>
            <h3 className="font-semibold mb-2">Mapping Details</h3>
            <div className="space-y-2 text-sm">
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
                <div className="text-muted-foreground">Loading additional details...</div>
              )}
              {conceptDetail && !isLoading && (
                <>
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
                      label="Confidence"
                      value={conceptDetail.confidence}
                    />
                  </div>
                  <div>
                    <InfoItem
                      label="Description"
                      value={conceptDetail.description}
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
                  <hr className="my-4" />
                  <h3 className="font-semibold mb-2">Concept Details</h3>
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
          <div className="pt-4 border-t">
            {onDelete && (

                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleDelete}
                  className="w-full mt-4"
                >
                  <Cross2Icon className="mr-2 h-4 w-4" />
                  Delete Concept
                </Button>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
} 
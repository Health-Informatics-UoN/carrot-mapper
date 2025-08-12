import React, { useOptimistic } from "react";
import { deleteConceptV3 } from "@/api/concepts";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/error";
import { Cross2Icon } from "@radix-ui/react-icons";
import { toast } from "sonner";
import { ConceptDetailsSheet } from "./ConceptDetailsSheet";

export function ConceptTagsV3({
  concepts,
  scanReportId,
  tableId,
  fieldId,
  valueId,
}: {
  concepts: ScanReportConceptV3[];
  scanReportId: string;
  tableId: string;
  fieldId: number;
  valueId: number;
}) {
  const [optimisticConcepts, setOptimisticConcepts] = useOptimistic(
    concepts,
    (state, conceptIdToDelete: number) =>
      state.filter((concept) => concept.id !== conceptIdToDelete)
  );

  const handleDelete = async (conceptId: number) => {
    try {
      setOptimisticConcepts(conceptId);
      await deleteConceptV3(
        conceptId,
        `/scanreports/${scanReportId}/tables/${tableId}/fields/${fieldId}/beta`
      );
      toast.success("Concept Id Deleted");
    } catch (error) {
      const errorObj = JSON.parse((error as ApiError).message);
      toast.error(
        `Unable to delete Concept id from value Error: ${errorObj.detail}`
      );
      console.error(error);
    }
  };

  return optimisticConcepts && optimisticConcepts.length > 0 ? (
    <div className="flex flex-col items-start">
      {optimisticConcepts.map((concept) => (
        <ConceptDetailsSheet
          key={concept.id}
          concept={concept}
          scanReportId={scanReportId}
          tableId={tableId}
          fieldId={fieldId.toString()}
          valueId={valueId}
        >
          <div className="p-0 w-full justify-start">
            <div
              className={`w-fit max-w-[300px] rounded-md border px-2.5 py-0.5 text-xs font-semibold relative ${
                concept.creation_type === "V"
                  ? "bg-rose-200 hover:bg-rose-200 text-black"
                  : concept.creation_type === "M"
                  ? "bg-blue-200 hover:bg-blue-200 text-black"
                  : concept.creation_type === "R"
                  ? "bg-emerald-200 hover:bg-emerald-200 text-black"
                  : ""
              } ${concepts.length > 1 && "my-[1px]"}`}
              key={concept.concept.concept_code}
            >
              <div className="pr-2">
                <span className="font-semibold">
                  {concept.concept.concept_id}
                </span>
                <span className="ml-1 text-wrap break-words">
                  {concept.concept.concept_name}
                </span>
                <span className="ml-1 text-xs opacity-80">
                  ({concept.creation_type})
                </span>
              </div>
              <Button
                size="icon"
                variant="ghost"
                onClick={async (e) => {
                  e.stopPropagation();
                  await handleDelete(concept.id);
                }}
                className="absolute top-0 right-0 h-auto p-0 pt-0.5 w-auto min-w-0 hover:text-red-600 text-black"
              >
                <Cross2Icon />
              </Button>
            </div>
          </div>
        </ConceptDetailsSheet>
      ))}
    </div>
  ) : (
    <></>
  );
}

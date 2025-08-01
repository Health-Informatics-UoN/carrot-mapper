import React, { lazy, useOptimistic } from "react";
import { deleteConceptV3 } from "@/api/concepts";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/error";
import { Cross2Icon } from "@radix-ui/react-icons";
import { toast } from "sonner";
import { ConceptDetailsSheet } from "./ConceptDetailsSheet";

const LazyBadge = lazy(() =>
  import("@/components/ui/badge").then((module) => ({ default: module.Badge })),
);

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
      state.filter((concept) => concept.id !== conceptIdToDelete),
  );

  const handleDelete = async (conceptId: number) => {
    try {
      setOptimisticConcepts(conceptId);
      await deleteConceptV3(
        conceptId,
        `/scanreports/${scanReportId}/tables/${tableId}/fields/${fieldId}/beta`,
      );
      toast.success("Concept Id Deleted");
    } catch (error) {
      const errorObj = JSON.parse((error as ApiError).message);
      toast.error(
        `Unable to delete Concept id from value Error: ${errorObj.detail}`,
      );
      console.error(error);
    }
  };

  return optimisticConcepts && optimisticConcepts.length > 0 ? (
    <div className="flex flex-col items-start w-[250px]">
      {optimisticConcepts.map((concept) => (
        <ConceptDetailsSheet
          key={concept.id}
          concept={concept}
          onDelete={handleDelete}
          scanReportId={scanReportId}
          tableId={tableId}
          fieldId={fieldId.toString()}
          valueId={valueId}
        >
          <Button
            variant="ghost"
            className="p-0 h-auto w-full justify-start"
          >
            <LazyBadge
              className={`${
                concept.creation_type === "V"
                  ? "bg-carrot-vocab hover:bg-carrot-vocab dark:bg-carrot-vocab dark:text-white"
                  : concept.creation_type === "M"
                    ? "bg-carrot-manual hover:bg-carrot-manual dark:bg-carrot-manual dark:text-white"
                    : concept.creation_type === "R"
                      ? "bg-carrot-reuse hover:bg-carrot-reuse dark:bg-carrot-reuse dark:text-white"
                      : ""
              } ${concepts.length > 1 && "my-[1px]"}`}
              key={concept.concept.concept_code}
            >
              <p className="pl-2 pr-1 py-1">{`${concept.concept.concept_id} ${concept.concept.concept_name} (${concept.creation_type})`}</p>
              <Button
                size="icon"
                variant="ghost"
                onClick={async (e) => {
                  e.stopPropagation();
                  await handleDelete(concept.id);
                }}
                className="dark:text-white"
              >
                <Cross2Icon />
              </Button>
            </LazyBadge>
          </Button>
        </ConceptDetailsSheet>
      ))}
    </div>
  ) : (
    <></>
  );
}

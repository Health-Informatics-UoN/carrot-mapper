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
                  ? "bg-pink-600 hover:bg-pink-600 text-white"
                  : concept.creation_type === "M"
                    ? "bg-sky-700 hover:bg-sky-700 text-white"
                    : concept.creation_type === "R"
                      ? "bg-emerald-700 hover:bg-emerald-700 text-white"
                      : ""
              } ${concepts.length > 1 && "my-[1px]"} p-1`}
              key={concept.concept.concept_code}
            >
              <p className="">{`${concept.concept.concept_id} ${concept.concept.concept_name} (${concept.creation_type})`}</p>
              <Cross2Icon
               onClick={async (e) => {
                  e.stopPropagation();
                  await handleDelete(concept.id);
                }}
              />
            </LazyBadge>
          </Button>
        </ConceptDetailsSheet>
      ))}
    </div>
  ) : (
    <></>
  );
}

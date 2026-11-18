import { ArrowLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { STATIC_DIALOG_STYLE } from "@/constants/mapping-registry";
import type { Mapping, MappingSet } from "@/types/mapping-registry";
import { Detail } from "./detail";

type MappingSetDetailsDialogProps = {
  /** The mapping set to show; null closes the dialog. */
  mappingSet: MappingSet | null;
  onClose: () => void;
  onBackToMapping?: () => void;
  onSelectMapping: (mapping: Mapping) => void;
};

export function MappingSetDetailsDialog({
  mappingSet,
  onClose,
  onBackToMapping,
  onSelectMapping,
}: MappingSetDetailsDialogProps) {
  return (
    <Dialog open={mappingSet !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="max-h-[calc(100svh-2rem)] w-[calc(100%-2rem)] overflow-y-auto duration-200 sm:max-w-2xl"
        style={STATIC_DIALOG_STYLE}
      >
        <DialogHeader className="pr-8 text-left">
          <DialogTitle>Mapping set details</DialogTitle>
          <DialogDescription>Published mapping set and its associated mappings.</DialogDescription>
        </DialogHeader>

        {mappingSet && (
          <div className="space-y-5">
            {onBackToMapping && (
              <Button type="button" variant="ghost" size="sm" onClick={onBackToMapping} className="-ml-2">
                <ArrowLeft className="size-4" /> Back to mapping
              </Button>
            )}
            <div className="rounded-lg border p-4">
              <h3 className="text-lg font-semibold">{mappingSet.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{mappingSet.description}</p>
            </div>

            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Detail label="Published by" value={mappingSet.publisher} />
              <Detail label="Version" value={mappingSet.version} />
              <Detail label="License" value={mappingSet.license} />
              <Detail label="Published on" value={mappingSet.publishedAt} />
              <Detail label="Mappings" value={String(mappingSet.mappings.length)} />
            </dl>

            <div className="border-t pt-5">
              <h4 className="mb-3 font-semibold">Mappings in this set</h4>
              <div className="space-y-2">
                {mappingSet.mappings.map((mapping) => (
                  <button
                    key={mapping.id}
                    type="button"
                    onClick={() => onSelectMapping(mapping)}
                    className="flex w-full items-center justify-between gap-3 rounded-md border p-3 text-left hover:bg-muted/50"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-semibold">
                        {mapping.sourceTerm} → {mapping.targetConcept}
                      </p>
                      <p className="text-xs text-muted-foreground">OMOP concept ID: {mapping.conceptId}</p>
                    </div>
                    <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

import { ArrowDown, ArrowRight, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { STATIC_DIALOG_STYLE } from "@/constants/mapping-registry";
import type { Mapping } from "@/types/mapping-registry";
import { Detail } from "./detail";

type MappingDetailsDialogProps = {
  /** The mapping to show; null closes the dialog. */
  mapping: Mapping | null;
  onClose: () => void;
  onViewSet: (mapping: Mapping) => void;
};

export function MappingDetailsDialog({
  mapping,
  onClose,
  onViewSet,
}: MappingDetailsDialogProps) {
  return (
    <Dialog open={mapping !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="max-h-[calc(100svh-2rem)] w-[calc(100%-2rem)] overflow-y-auto duration-200 sm:max-w-xl"
        style={STATIC_DIALOG_STYLE}
      >
        <DialogHeader className="pr-8 text-left">
          <DialogTitle>Mapping details</DialogTitle>
          <DialogDescription>
            View a published mapping and its metadata.
          </DialogDescription>
        </DialogHeader>

        {mapping && (
          <div className="space-y-6">
            <div className="rounded-xl border bg-card p-5 shadow-sm">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-8">
                <div className="min-w-0 sm:max-w-[40%]">
                  <p className="text-xs font-medium text-muted-foreground">Source term</p>
                  <h3 className="mt-1 text-lg font-semibold">{mapping.sourceTerm}</h3>
                  <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{mapping.subjectId}</p>
                </div>
                <div aria-hidden="true" className="flex size-10 shrink-0 self-center items-center justify-center rounded-full border border-primary/20 bg-primary/5 text-primary shadow-sm sm:self-auto">
                  <ArrowDown className="size-4 sm:hidden" />
                  <ArrowRight className="hidden size-5 sm:block" />
                </div>
                <div className="min-w-0 sm:flex-1">
                  <p className="text-xs font-medium text-muted-foreground">OMOP concept</p>
                  <p className="mt-1 text-base font-semibold">{mapping.targetConcept}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    OMOP concept ID: {mapping.conceptId} · {mapping.vocabulary}
                  </p>
                </div>
              </div>
            </div>

            <div>
              <h4 className="mb-3 font-semibold">Mapping metadata</h4>
              <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Detail label="Predicate" value={mapping.predicate} />
                <Detail label="Justification" value={mapping.justification} />
                <Detail label="Vocabulary version" value={mapping.vocabularyVersion} />
                <Detail label="Published on" value={mapping.publishedAt} />
                <Detail label="Canonical IRI" value={mapping.canonicalIri} />
              </dl>
            </div>

            <div className="border-t pt-5">
              <h4 className="mb-3 font-semibold">Publication and mapping set</h4>
              <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Detail label="Published by" value={mapping.publisher} />
                <Detail label="Mapping set" value={mapping.mappingSet} />
                <Detail label="Version" value={mapping.mappingSetVersion} />
                <Detail label="License" value={mapping.license} />
              </dl>
              <Button type="button" variant="outline" className="mt-4" onClick={() => onViewSet(mapping)}>
                <Layers className="size-4" /> View mapping set
              </Button>
            </div>

          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

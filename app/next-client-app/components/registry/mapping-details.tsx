import Link from "next/link";
import { ArrowDown, ArrowLeft, ArrowRight, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Mapping, MappingSet } from "@/types/mapping-registry";
import { Detail } from "./detail";
import { RegistryBreadcrumbs } from "./registry-breadcrumbs";
import { BackToResultsLink } from "./back-to-results-link";

export function MappingDetails({ mapping, parentSet }: { mapping: Mapping; parentSet?: MappingSet }) {
  return (
    <div className="mx-auto w-full max-w-2xl space-y-5 py-6">
      <RegistryBreadcrumbs
        items={
          parentSet
            ? [
                { label: "Registry", href: "/registry" },
                { label: "Mapping sets", href: "/registry/mapping-sets" },
                { label: parentSet.title, href: `/registry/mapping-sets/${parentSet.id}` },
                { label: mapping.sourceTerm },
              ]
            : [
                { label: "Registry", href: "/registry" },
                { label: "Mappings", href: "/registry/mappings" },
                { label: mapping.sourceTerm },
              ]
        }
      />
      {parentSet ? (
        <Link
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          href={`/registry/mapping-sets/${parentSet.id}`}
        >
          <ArrowLeft className="size-4" /> Back to {parentSet.title}
        </Link>
      ) : (
        <BackToResultsLink fallbackHref="/registry/mappings" sessionKey="registry:lastMappingsUrl" />
      )}

      <div className="space-y-6">
        <div className="rounded-xl border bg-card p-5 shadow-sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-8">
            <div className="min-w-0 sm:max-w-[40%]">
              <p className="text-xs font-medium text-muted-foreground">Source term</p>
              <h1 className="mt-1 text-lg font-semibold">{mapping.sourceTerm}</h1>
              <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{mapping.subjectId}</p>
            </div>
            <div aria-hidden="true" className="flex size-10 shrink-0 self-center items-center justify-center rounded-full border border-primary/20 bg-primary/5 text-primary shadow-sm sm:self-auto">
              <ArrowDown className="size-4 sm:hidden" />
              <ArrowRight className="hidden size-5 sm:block" />
            </div>
            <div className="min-w-0 sm:flex-1">
              <p className="text-xs font-medium text-muted-foreground">OMOP concept</p>
              <p className="mt-1 text-base font-semibold">{mapping.targetConcept}</p>
              <p className="mt-1 text-sm text-muted-foreground">OMOP concept ID: {mapping.conceptId} · {mapping.vocabulary}</p>
            </div>
          </div>
        </div>

        <div>
          <h2 className="mb-3 text-lg font-semibold">Mapping metadata</h2>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Detail label="Predicate" value={mapping.predicate} />
            <Detail label="Justification" value={mapping.justification} />
            <Detail label="Vocabulary version" value={mapping.vocabularyVersion} />
            <Detail label="Published on" value={mapping.publishedAt} />
            <Detail label="Canonical IRI" value={mapping.canonicalIri} />
          </dl>
        </div>

        <div className="border-t pt-5">
          <h2 className="mb-3 text-lg font-semibold">Publication and mapping set</h2>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Detail label="Published by" value={mapping.publisher} />
            <Detail label="Mapping set" value={mapping.mappingSet} />
            <Detail label="Version" value={mapping.mappingSetVersion} />
            <Detail label="License" value={mapping.license} />
          </dl>
          <Button asChild variant="outline" className="mt-4">
            <Link href={parentSet
              ? `/registry/mapping-sets/${mapping.mappingSetId}`
              : `/registry/mapping-sets/${mapping.mappingSetId}?fromMapping=${encodeURIComponent(mapping.id)}`}>
              <Layers className="size-4" /> View mapping set
            </Link>
          </Button>
        </div>

      </div>
    </div>
  );
}

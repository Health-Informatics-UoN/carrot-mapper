import Link from "next/link";
import { ArrowLeft, ChevronRight, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Mapping, MappingSet } from "@/types/mapping-registry";
import { Detail } from "./detail";
import { RegistryBreadcrumbs } from "./registry-breadcrumbs";
import { BackToResultsLink } from "./back-to-results-link";

export function MappingSetDetails({
  mappingSet,
  originMapping,
}: {
  mappingSet: MappingSet;
  originMapping?: Mapping;
}) {
  return (
    <div className="mx-auto w-full max-w-2xl space-y-5 py-6">
      <RegistryBreadcrumbs
        items={
          originMapping
            ? [
                { label: "Registry", href: "/registry" },
                { label: "Mappings", href: "/registry/mappings" },
                {
                  label: originMapping.sourceTerm,
                  href: `/registry/mappings/${originMapping.id}`,
                },
                { label: mappingSet.title },
              ]
            : [
                { label: "Registry", href: "/registry" },
                { label: "Mapping sets", href: "/registry/mapping-sets" },
                { label: mappingSet.title },
              ]
        }
      />
      {originMapping ? (
        <Link
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          href={`/registry/mappings/${originMapping.id}`}
        >
          <ArrowLeft className="size-4" /> Back to {originMapping.sourceTerm}
        </Link>
      ) : (
        <BackToResultsLink
          fallbackHref="/registry/mapping-sets"
          sessionKey="registry:lastMappingSetsUrl"
        />
      )}

      <div className="space-y-5">
        <div className="rounded-lg border p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-lg font-semibold">{mappingSet.title}</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                {mappingSet.description}
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="shrink-0"
            >
              <Download className="size-4" /> Download SSSOM
            </Button>
          </div>
        </div>

        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Detail label="Published by" value={mappingSet.publisher} />
          <Detail label="Version" value={mappingSet.version} />
          <Detail label="License" value={mappingSet.license} />
          <Detail label="Published on" value={mappingSet.publishedAt} />
          <Detail label="Mappings" value={String(mappingSet.mappings.length)} />
        </dl>

        <div className="border-t pt-5">
          <h2 className="mb-3 text-lg font-semibold">Mappings in this set</h2>
          <div className="space-y-2">
            {mappingSet.mappings.map((mapping) => (
              <Button
                key={mapping.id}
                asChild
                variant="outline"
                className="h-auto w-full justify-between gap-3 p-3 text-left"
              >
                <Link
                  href={`/registry/mappings/${mapping.id}?fromMappingSet=${encodeURIComponent(mappingSet.id)}`}
                >
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">
                      {mapping.sourceTerm} → {mapping.targetConcept}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      OMOP concept ID: {mapping.conceptId}
                    </p>
                  </div>
                  <ChevronRight className="size-4 shrink-0" />
                </Link>
              </Button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

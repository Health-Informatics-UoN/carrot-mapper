"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRegistrySearch } from "@/lib/hooks/useRegistrySearch";
import type { View } from "@/types/mapping-registry";
import { RegistryHero } from "./registry-hero";
import { RegistrySearchBar } from "./registry-search-bar";
import { RegistryResults } from "./registry-results";

export function RegistryListPage({ view }: { view: View }) {
  const router = useRouter();
  const registry = useRegistrySearch(view);
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col pb-3">
      <div className="mx-auto w-full max-w-3xl pt-4 pb-5">
        <RegistryHero compact />
        <RegistrySearchBar
          view={view}
          field={registry.field}
          query={registry.query}
          isLoading={registry.isLoading}
          onFieldChange={registry.changeField}
          onQueryChange={registry.changeQuery}
        />

        <div className="mt-4 flex justify-center">
          <Button asChild variant="outline">
            <Link href="/registry">
              <ArrowLeft className="size-4" /> Back to Registry
            </Link>
          </Button>
        </div>
      </div>

      <RegistryResults
        view={view}
        query={registry.query}
        isLoading={registry.isLoading}
        mappings={registry.mappings}
        mappingSets={registry.mappingSets}
        total={registry.total}
        sort={registry.sort}
        onSortChange={registry.setSort}
        onBrowse={(nextView) => {
          router.push(
            nextView === "mappings"
              ? "/registry/mappings"
              : "/registry/mapping-sets",
            { scroll: false },
          );
        }}
      />
    </div>
  );
}

export function RegistryListPageWithSuspense({ view }: { view: View }) {
  return (
    <Suspense fallback={null}>
      <RegistryListPage view={view} />
    </Suspense>
  );
}

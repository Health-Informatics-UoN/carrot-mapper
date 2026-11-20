"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { RegistryDataContent } from "./registry-data-content";
import { RegistryHero } from "./registry-hero";
import { RegistryLandingActions } from "./registry-landing-actions";
import { RegistrySearchBar } from "./registry-search-bar";
import type { RegistryStats, SearchField } from "@/types/mapping-registry";

export function RegistryLandingPage({ stats }: { stats: RegistryStats }) {
  const router = useRouter();
  const [field, setField] = useState<SearchField>("sourceTerm");
  const [query, setQuery] = useState("");

  function submitSearch() {
    const params = new URLSearchParams();
    const trimmed = query.trim();
    if (trimmed) params.set("q", trimmed);
    if (field !== "sourceTerm") params.set("field", field);
    const search = params.toString();
    router.push(`/registry/mappings${search ? `?${search}` : ""}`);
  }

  return (
    <div className="relative flex w-full flex-1 flex-col pb-3">
      <div className="flex justify-end pt-3 md:-mr-4 lg:absolute lg:-right-4 lg:top-0 lg:z-10 lg:mr-0 lg:pt-0">
        <RegistryDataContent stats={stats} />
      </div>

      <div className="mx-auto grid w-full max-w-3xl flex-1 grid-rows-[1fr_auto_1fr] py-6">
        <RegistryHero compact={false} />
        <form
          onSubmit={(event) => {
            event.preventDefault();
            submitSearch();
          }}
        >
          <RegistrySearchBar
            mode="submit"
            view="mappings"
            field={field}
            query={query}
            isLoading={false}
            onFieldChange={setField}
            onQueryChange={setQuery}
          />
        </form>
        <RegistryLandingActions
          onBrowse={(view) => router.push(view === "mappings" ? "/registry/mappings" : "/registry/mapping-sets")}
        />
      </div>
    </div>
  );
}

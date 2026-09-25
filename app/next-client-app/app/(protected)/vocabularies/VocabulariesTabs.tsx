"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { navigateWithSearchParam } from "@/lib/client-utils";
import { useRouter, useSearchParams } from "next/navigation";

interface VocabulariesTabsProps {
  activeTab: "vocabularies" | "search";
  vocabulariesTab: React.ReactNode;
  searchTab: React.ReactNode;
}

export function VocabulariesTabs({
  activeTab,
  vocabulariesTab,
  searchTab,
}: VocabulariesTabsProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  return (
    <Tabs
      value={activeTab}
      onValueChange={(value) =>
        navigateWithSearchParam(
          "tab",
          value === "vocabularies" ? "" : value,
          router,
          searchParams,
        )
      }
    >
      <TabsList>
        <TabsTrigger value="vocabularies">Vocabularies</TabsTrigger>
        <TabsTrigger value="search">Search Concepts</TabsTrigger>
      </TabsList>
      <TabsContent value="vocabularies">{vocabulariesTab}</TabsContent>
      <TabsContent value="search">{searchTab}</TabsContent>
    </Tabs>
  );
}

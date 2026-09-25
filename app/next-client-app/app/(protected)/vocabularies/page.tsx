import { DataTable } from "@/components/data-table";
import { columns } from "./columns";
import { objToQuery } from "@/lib/client-utils";
import { DataTableFilter } from "@/components/data-table/DataTableFilter";
import { Library } from "lucide-react";
import { getVocabulariesList } from "@/api/vocabularies";
import { Metadata } from "next";
import { EmptyState } from "@/components/ui/empty-state";
import { VocabulariesTabs } from "./VocabulariesTabs";
import { ConceptSearchTab } from "./ConceptSearchTab";

export const metadata: Metadata = {
  title: "Vocabularies | Carrot Mapper",
  description: "OMOP vocabularies loaded into Carrot Mapper",
};

interface VocabularyListProps {
  searchParams?: Promise<FilterParameters & ConceptSearchParameters>;
}

export default async function Vocabularies(props: VocabularyListProps) {
  const searchParams = await props.searchParams;
  const activeTab = searchParams?.tab === "search" ? "search" : "vocabularies";

  return (
    <div className="space-y-2">
      <div className="flex font-semibold text-xl items-center">
        <Library className="mr-2 text-orange-700" />
        <h2>Vocabularies</h2>
      </div>
      <VocabulariesTabs
        activeTab={activeTab}
        vocabulariesTab={
          activeTab === "vocabularies" ? (
            <VocabulariesList searchParams={searchParams} />
          ) : null
        }
        searchTab={
          activeTab === "search" ? (
            <ConceptSearchTab searchParams={searchParams ?? {}} />
          ) : null
        }
      />
    </div>
  );
}

async function VocabulariesList({
  searchParams,
}: {
  searchParams?: FilterParameters;
}) {
  const defaultParams = {
    page_size: 50,
  };
  const combinedParams = { ...defaultParams, ...searchParams };
  const query = objToQuery(combinedParams);
  const vocabularies = await getVocabulariesList(query);

  const filter = <DataTableFilter filter="vocabulary_name" />;

  return vocabularies.results.length > 0 ? (
    <DataTable
      columns={columns}
      data={vocabularies.results}
      count={vocabularies.count}
      Filter={filter}
      defaultPageSize={50}
    />
  ) : (
    <EmptyState
      icon="library"
      title="No vocabularies loaded"
      description="No OMOP vocabularies were found. Contact your administrator to check the vocabulary table has been loaded."
    />
  );
}

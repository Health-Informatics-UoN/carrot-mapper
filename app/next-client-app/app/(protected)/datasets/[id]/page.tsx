import { columns } from "@/app/(protected)/scanreports/columns";
import { getScanReports } from "@/api/scanreports";
import { DataTable } from "@/components/data-table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { objToQuery } from "@/lib/client-utils";
import { ScanReportsTableFilter } from "@/components/scanreports/ScanReportsTableFilter";
import { FilterParameters } from "@/types/filter";
import { VisibilityState } from "@tanstack/react-table";
import { EmptyState } from "@/components/ui/empty-state";

interface DataSetListProps {
  params: Promise<{
    id: string;
  }>;
  searchParams?: Promise<{ status__in: string } & FilterParameters>;
}

export default async function DatasetSRList(props: DataSetListProps) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const { id } = params;
  const defaultPageSize = 30;

  const defaultParams = {
    hidden: false,
    page_size: defaultPageSize,
    parent_dataset: id
  };
  const combinedParams = { ...defaultParams, ...searchParams };

  const query = objToQuery(combinedParams);
  const scanReports = await getScanReports(query);
  const filter = <ScanReportsTableFilter filter="dataset" filterText="name" />;

  // Define which columns should be hidden by default
  const initialColumnVisibility: VisibilityState = {
    id: false,
    Dataset: false
  };

  return (
    <Tabs
      defaultValue={
        (searchParams as any)?.hidden
          ? (searchParams as any)?.hidden === "true"
            ? "archived"
            : "active"
          : "active"
      }
    >
      <TabsList>
        <a href="?hidden=false" className="h-full">
          <TabsTrigger value="active">Active Reports</TabsTrigger>
        </a>
        <a href="?hidden=true" className="h-full">
          <TabsTrigger value="archived">Archived Reports</TabsTrigger>
        </a>
      </TabsList>
      <TabsContent value="active">
        {scanReports.results.length > 0 ? (
          <DataTable
            columns={columns}
            data={scanReports.results}
            count={scanReports.count}
            Filter={filter}
            initialColumnVisibility={initialColumnVisibility}
            defaultPageSize={defaultPageSize}
          />
        ) : (
          <EmptyState
            icon="filescan"
            title="No scan reports in this dataset"
            description="No scan reports found in this dataset yet."
          />
        )}
      </TabsContent>
      <TabsContent value="archived">
        {scanReports.results.length > 0 ? (
          <DataTable
            columns={columns}
            data={scanReports.results}
            count={scanReports.count}
            Filter={filter}
            initialColumnVisibility={initialColumnVisibility}
            defaultPageSize={defaultPageSize}
          />
        ) : (
          <EmptyState
            icon="filescan"
            title="No archived reports"
            description="No archived scan reports found in this dataset. Active reports will appear here when archived."
          />
        )}
      </TabsContent>
    </Tabs>
  );
}

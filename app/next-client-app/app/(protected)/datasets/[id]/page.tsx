import { columns } from "../../scanreports/columns";
import { getScanReports } from "@/api/scanreports";
import { DataTable } from "@/components/data-table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { objToQuery } from "@/lib/client-utils";
import { ScanReportsTableFilter } from "@/components/scanreports/ScanReportsTableFilter";
import { FilterParameters } from "@/types/filter";

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

  const defaultParams = {
    hidden: false,
    page_size: 10,
    parent_dataset: id
  };
  const combinedParams = { ...defaultParams, ...searchParams };

  const query = objToQuery(combinedParams);
  const scanReports = await getScanReports(query);
  const filter = <ScanReportsTableFilter filter="dataset" filterText="name" />;

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
        <DataTable
          columns={columns}
          data={scanReports.results}
          count={scanReports.count}
          Filter={filter}
        />
      </TabsContent>
      <TabsContent value="archived">
        <DataTable
          columns={columns}
          data={scanReports.results}
          count={scanReports.count}
          Filter={filter}
        />
      </TabsContent>
    </Tabs>
  );
}

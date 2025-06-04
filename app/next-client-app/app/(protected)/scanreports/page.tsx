import { columns } from "./columns";
import { getScanReports } from "@/api/scanreports";
import { DataTable } from "@/components/data-table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { objToQuery } from "@/lib/client-utils";
import { ScanReportsTableFilter } from "@/components/scanreports/ScanReportsTableFilter";
import { FilterParameters } from "@/types/filter";
import { FileScan } from "lucide-react";

interface ScanReportsProps {
  searchParams?: Promise<{ status__in: string } & FilterParameters>;
}

export default async function ScanReports(props: ScanReportsProps) {
  const searchParams = await props.searchParams;
  const defaultPageSize = 10;
  const defaultParams = {
    hidden: false,
    page_size: defaultPageSize,
  };
  const combinedParams = { ...defaultParams, ...searchParams };

  const query = objToQuery(combinedParams);
  const scanReports = await getScanReports(query);
  const filter = <ScanReportsTableFilter filter="dataset" filterText="name" />;

  return (
    <div className="space-y-2">
      <div className="flex font-semibold text-xl items-center">
        <FileScan className="mr-2 text-green-700" />
        <h2>Scan Reports</h2>
      </div>

      <div className="my-3">
        <Tabs
          defaultValue={
            (searchParams as any)?.hidden
              ? (searchParams as any)?.hidden === "true"
                ? "archived"
                : "active"
              : "active"
          }
        >
          <TabsList className="mb-2">
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
              defaultPageSize={defaultPageSize}
            />
          </TabsContent>
          <TabsContent value="archived">
            <DataTable
              columns={columns}
              data={scanReports.results}
              count={scanReports.count}
              Filter={filter}
              defaultPageSize={defaultPageSize}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
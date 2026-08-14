import {
  getScanReportPermissions,
  getJobs,
  getScanReportTables,
} from "@/api/scanreports";
import { objToQuery } from "@/lib/client-utils";
import ScanReportsTableClient from "@/components/scanreports/ScanReportsTableClient";
import { DataTableFilter } from "@/components/data-table/DataTableFilter";
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage } from "@/components/ui/breadcrumb";

interface ScanReportsTableProps {
  params: Promise<{
    id: string;
  }>;
  searchParams?: Promise<FilterParameters>;
}

export default async function ScanReportsTable(props: ScanReportsTableProps) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const {
    id
  } = params;

  const defaultParams = {};

  const combinedParams = { ...defaultParams, ...searchParams };
  const query = objToQuery(combinedParams);
  const filter = <DataTableFilter filter="name" />;
  const [scanReportsTables, permissions, jobs] = await Promise.all([
    getScanReportTables(id, query),
    getScanReportPermissions(id),
    getJobs(id),
  ]);
  const scanReportsResult = scanReportsTables.results.map((table) => {
    table.permissions = permissions.permissions;
    if (jobs) {
      table.jobs = jobs;
    }

    return table;
  });

  return (
    <div>
      <Breadcrumb className="mb-3 hidden md:block">
        <BreadcrumbList>
          <BreadcrumbPage>
            Tables
          </BreadcrumbPage>
        </BreadcrumbList>
      </Breadcrumb>
      <ScanReportsTableClient
        scanReportId={id}
        Filter={filter}
        initialScanReportsResult={scanReportsResult}
        count={scanReportsTables.count}
      />
    </div>
  );
}

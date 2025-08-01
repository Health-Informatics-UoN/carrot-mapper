import {
  getScanReportPermissions,
  getJobs,
  getScanReportTables,
} from "@/api/scanreports";
import { objToQuery } from "@/lib/client-utils";
import { FilterParameters } from "@/types/filter";
import ScanReportsTableClient from "@/components/scanreports/ScanReportsTableClient";
import { DataTableFilter } from "@/components/data-table/DataTableFilter";
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage } from "@/components/ui/breadcrumb";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Scan Report | Carrot Mapper",
  description: "Scan report details",
};

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
  const scanReportsTables = await getScanReportTables(id, query);
  const permissions = await getScanReportPermissions(id);
  // Get data about jobs then inject it to the SR table data
  const jobs = await getJobs(id);
  const scanReportsResult = scanReportsTables.results.map((table) => {
    table.permissions = permissions.permissions;
    if (jobs) {
      table.jobs = jobs;
    }

    return table;
  });

  return (
    <div>
      <Breadcrumb className="mb-3">
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

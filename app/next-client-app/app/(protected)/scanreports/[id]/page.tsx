import {
  getScanReportPermissions,
  getJobs,
  getScanReportTables,
  getScanReport,
} from "@/api/scanreports";
import { objToQuery } from "@/lib/client-utils";
import { FilterParameters } from "@/types/filter";
import ScanReportsTableClient from "@/components/scanreports/ScanReportsTableClient";
import { DataTableFilter } from "@/components/data-table/DataTableFilter";

interface ScanReportsTableProps {
  params: {
    id: string;
  };
  searchParams?: FilterParameters;
}

export default async function ScanReportsTable({
  params: { id },
  searchParams,
}: ScanReportsTableProps) {
  const defaultParams = {};

  const combinedParams = { ...defaultParams, ...searchParams };
  const query = objToQuery(combinedParams);
  const filter = <DataTableFilter filter="name" />;
  const scanReportsTables = await getScanReportTables(id, query);
  const permissions = await getScanReportPermissions(id);
  // Get data about jobs then inject it to the SR table data
  const jobs = await getJobs(id);
  const scanReport = await getScanReport(id);
  const scanReportsResult = scanReportsTables.results.map((table) => {
    table.permissions = permissions.permissions;
    if (jobs) {
      table.jobs = jobs;
    }

    return table;
  });
  if (!scanReport) {
    return <div>Scan Report not found</div>;
  }

  return (
    <div>
      <div>
        <ScanReportsTableClient
          scanReportId={id}
          Filter={filter}
          initialScanReportsResult={scanReportsResult}
          count={scanReportsTables.count}
          uploadStatus={scanReport.upload_status}
        />
      </div>
    </div>
  );
}

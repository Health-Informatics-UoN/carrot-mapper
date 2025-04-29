"use client";

import { useEffect, useState } from "react";

import { DataTable } from "@/components/data-table";
import { RefreshButton } from "../jobs/RefreshButton";
import { columns } from "@/app/(protected)/scanreports/[id]/columns";

export default function ScanReportsTableClient({
  initialScanReportsResult,
  scanReportId,
  Filter,
  count,
  uploadStatus,
}: {
  initialScanReportsResult: ScanReportTable[];
  scanReportId: string;
  Filter: JSX.Element;
  count: number;
  uploadStatus?: ScanReport["upload_status"];
}) {
  const [scanReportsResult, setScanReportsResult] = useState(
    initialScanReportsResult
  );

  useEffect(() => {
    setScanReportsResult(initialScanReportsResult);
  }, [initialScanReportsResult]);

  const handleJobsRefresh = (updatedJobs: Job[]) => {
    // Update the jobs for each table row
    const updatedScanReportsResult = scanReportsResult.map((table) => ({
      ...table,
      jobs: updatedJobs,
    }));

    setScanReportsResult(updatedScanReportsResult);
  };

  return (
    <div>
      <DataTable
        columns={columns}
        data={scanReportsResult}
        count={count}
        RefreshButton={
          <RefreshButton
            scanReportId={scanReportId}
            onJobsRefresh={handleJobsRefresh}
          />
        }
        linkPrefix="tables/"
        Filter={Filter}
        uploadStatus={uploadStatus}
      />
    </div>
  );
}

"use client";

import { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { columns as scanReportColumns } from "./columns";

const scanReportColumn: ColumnDef<ActivityLog> = {
  id: "Scan Report",
  header: ({ column }) => (
    <DataTableColumnHeader column={column} title="Scan Report" />
  ),
  cell: ({ row }) => {
    const { scope_type, scope_id, scan_report_name } = row.original;
    if (scope_type !== "scanreport") return "—";
    return (
      <Button variant="link" className="h-auto p-0" asChild>
        <Link href={`/scanreports/${scope_id}`}>
          {scan_report_name ?? `Scan report #${scope_id}`}
        </Link>
      </Button>
    );
  },
  enableHiding: true,
  enableSorting: false,
};

// Same as the scan-report-page columns, but with a "Scan Report" column
// inserted: a dataset's log feed spans many scan reports, so every row
// needs to say which one it refers to.
export const datasetColumns: ColumnDef<ActivityLog>[] = [
  scanReportColumns[0],
  scanReportColumns[1],
  scanReportColumn,
  ...scanReportColumns.slice(2),
];

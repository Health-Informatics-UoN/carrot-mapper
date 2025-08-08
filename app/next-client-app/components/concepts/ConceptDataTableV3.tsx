"use client";

import { DataTable } from "@/components/data-table";

interface CustomDataTableProps<T> {
  scanReportsData: ScanReportValueV3[];
  canEdit: boolean;
  count: number;
  defaultPageSize: 10 | 20 | 30 | 40 | 50;
  columns: (
    tableId: string,
    canEdit: boolean,
    scanReportId: string,
  ) => any;
  tableId: string;
  scanReportId: string;
  Filter: JSX.Element;
}

export function ConceptDataTableV3<
  T extends { id: number; concepts?: ScanReportConceptV3[] },
>({
  scanReportsData,
  canEdit,
  count,
  defaultPageSize,
  columns,
  tableId,
  scanReportId,
  Filter,
}: CustomDataTableProps<T>) {

  return (
    <div>
      <DataTable
        columns={columns(tableId, canEdit, scanReportId)}
        data={scanReportsData}
        count={count}
        Filter={Filter}
        defaultPageSize={defaultPageSize}
      />
    </div>
  );
}

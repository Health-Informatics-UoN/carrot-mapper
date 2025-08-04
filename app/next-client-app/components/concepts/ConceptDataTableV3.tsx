"use client";

import { DataTable } from "@/components/data-table";
import { DataTableFilter } from "@/components/data-table/DataTableFilter";

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
  filterCol: string;
  filterText: string;
  tableId: string;
  scanReportId: string;
}

export function ConceptDataTableV3<
  T extends { id: number; concepts?: ScanReportConceptV3[] },
>({
  scanReportsData,
  canEdit,
  count,
  defaultPageSize,
  columns,
  filterCol,
  filterText,
  tableId,
  scanReportId,
}: CustomDataTableProps<T>) {
  const filter = <DataTableFilter filter={filterCol} filterText={filterText} />;

  return (
    <div>
      <DataTable
        columns={columns(tableId, canEdit, scanReportId)}
        data={scanReportsData}
        count={count}
        Filter={filter}
        defaultPageSize={defaultPageSize}
      />
    </div>
  );
}

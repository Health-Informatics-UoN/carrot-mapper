"use client";

import type { JSX } from "react";
import { useOptimistic } from "react";
import { DataTable } from "@/components/data-table";

interface CustomDataTableProps<T> {
  scanReportsData: T[];
  canEdit: boolean;
  count: number;
  defaultPageSize: 10 | 20 | 30 | 40 | 50;
  columns: (
    tableId: string,
    canEdit: boolean,
    scanReportId: string,
    dispatch: React.Dispatch<ConceptTableAction>,
  ) => any;
  tableId: string;
  scanReportId: string;
  Filter: JSX.Element;
}

function conceptsReducer<
  T extends { id: number; concepts?: ScanReportConceptV3[] },
>(rows: T[], action: ConceptTableAction): T[] {
  return rows.map((row) => {
    if (row.id !== action.rowId) return row;
    if (action.type === "add") {
      return { ...row, concepts: [...(row.concepts ?? []), action.concept] };
    }
    return {
      ...row,
      concepts: (row.concepts ?? []).filter((c) => c.id !== action.conceptId),
    };
  });
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
  // Add/delete both apply here, instantly, instead of waiting for the
  // server-action-triggered page revalidation to round-trip and re-render.
  const [optimisticData, dispatchConceptAction] = useOptimistic<
    T[],
    ConceptTableAction
  >(scanReportsData, conceptsReducer);

  return (
    <div>
      <DataTable
        columns={columns(tableId, canEdit, scanReportId, dispatchConceptAction)}
        data={optimisticData}
        count={count}
        Filter={Filter}
        defaultPageSize={defaultPageSize}
      />
    </div>
  );
}

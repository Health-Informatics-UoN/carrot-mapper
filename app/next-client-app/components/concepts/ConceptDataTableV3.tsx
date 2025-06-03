"use client";

import { DataTable } from "@/components/data-table";
import { DataTableFilter } from "@/components/data-table/DataTableFilter";

interface CustomDataTableProps<T> {
  scanReportsData: ScanReportValueV3[];
  canEdit: boolean;
  count: number;
  defaultPageSize: 10 | 20 | 30 | 40 | 50;
  columns: (
    // addConcept: (newConcept: ScanReportConcept, newConFilter: Concept) => void,
    // deleteConcept: (id: number) => void,
    tableId: string,
    canEdit: boolean,
  ) => any;
  filterCol: string;
  filterText: string;
  linkPrefix?: string;
  tableId: string;
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
  linkPrefix,
  tableId,
}: CustomDataTableProps<T>) {
  const filter = <DataTableFilter filter={filterCol} filterText={filterText} />;

  // const deleteConcept = (id: number) => {
  //   // filter it out.
  //   const updatedConcepts = neededConcepts.filter(
  //     (concept) => concept.id !== id
  //   );
  //   setNeededConcepts(updatedConcepts);
  // };

  // const addConcept = (newConcept: ScanReportConcept, newConFilter: Concept) => {
  //   // merge it.

  //   const updatedConcepts = [...neededConcepts, newConcept];
  //   setNeededConcepts(updatedConcepts);

  //   const updatedConceptFilters = [...neededConceptFilter, newConFilter];
  //   setNeededConceptFilter(updatedConceptFilters);
  // };

  return (
    <div>
      <DataTable
        columns={columns(tableId, canEdit)}
        data={scanReportsData}
        count={count}
        Filter={filter}
        defaultPageSize={defaultPageSize}
        linkPrefix={linkPrefix}
      />
    </div>
  );
}

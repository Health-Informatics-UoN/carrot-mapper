"use client";

import { DataTable } from "@/components/data-table";
import { DataTableFilter } from "@/components/data-table/DataTableFilter";
import { addConceptsToResults } from "@/lib/concept-utils";
import { useEffect, useState } from "react";

interface CustomDataTableProps<T> {
  scanReportsData: T[];
  scanReportsConcepts: ScanReportConcept[];
  conceptsFilter: Concept[];
  permissions: PermissionsResponse;
  count: number;
  defaultPageSize: 10 | 20 | 30 | 40 | 50;
  columns: (
    addConcept: (newConcept: ScanReportConcept, newConFilter: Concept) => void,
    deleteConcept: (id: number) => void,
    tableId: string
  ) => any;
  filterCol: string;
  filterText: string;
  linkPrefix?: string;
  tableId: string;
}

export function ConceptDataTable<
  T extends { id: number; concepts?: Concept[]; permissions: Permission[] }
>({
  scanReportsData,
  scanReportsConcepts,
  conceptsFilter,
  permissions,
  count,
  defaultPageSize,
  columns,
  filterCol,
  filterText,
  linkPrefix,
  tableId,
}: CustomDataTableProps<T>) {
  const filter = <DataTableFilter filter={filterCol} filterText={filterText} />;

  // Set the needed Concepts and Concepts filter in state, so we can mutate them individually.
  const [neededConcepts, setNeededConcepts] = useState(scanReportsConcepts);
  const [neededConceptFilter, setNeededConceptFilter] =
    useState(conceptsFilter);

  // Necessary for pagination
  useEffect(() => {
    setNeededConcepts(scanReportsConcepts);
  }, [scanReportsConcepts]);

  useEffect(() => {
    setNeededConceptFilter(conceptsFilter);
  }, [conceptsFilter]);

  const deleteConcept = (id: number) => {
    // filter it out.
    const updatedConcepts = neededConcepts.filter(
      (concept) => concept.id !== id
    );
    setNeededConcepts(updatedConcepts);
  };

  const addConcept = (newConcept: ScanReportConcept, newConFilter: Concept) => {
    // merge it.

    const updatedConcepts = [...neededConcepts, newConcept];
    setNeededConcepts(updatedConcepts);

    const updatedConceptFilters = [...neededConceptFilter, newConFilter];
    setNeededConceptFilter(updatedConceptFilters);
  };

  const scanReportsResult = addConceptsToResults(
    scanReportsData,
    neededConcepts,
    neededConceptFilter,
    permissions
  );

  return (
    <div>
      <DataTable
        columns={columns(addConcept, deleteConcept, tableId)}
        data={scanReportsResult}
        count={count}
        Filter={filter}
        defaultPageSize={defaultPageSize}
        linkPrefix={linkPrefix}
      />
    </div>
  );
}

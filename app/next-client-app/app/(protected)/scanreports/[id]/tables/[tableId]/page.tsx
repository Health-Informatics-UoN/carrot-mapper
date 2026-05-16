import { columns } from "./columns";
import {
  getScanReportFields,
  getScanReportFieldsV3,
  getScanReportPermissions,
  getScanReportTable,
} from "@/api/scanreports";
import { objToQuery } from "@/lib/client-utils";
import {
  getAllConceptsFiltered,
  getAllScanReportConcepts,
} from "@/api/concepts";
import { ConceptDataTable } from "@/components/concepts/ConceptDataTable";
import { TableBreadcrumbs } from "@/components/scanreports/TableBreadcrumbs";
import { ConceptDataTableV3 } from "@/components/concepts/ConceptDataTableV3";
import { ConceptDataFilter } from "@/components/concepts/ConceptDataFilter";

interface ScanReportsFieldProps {
  params: Promise<{
    id: string;
    tableId: string;
  }>;
  searchParams?: Promise<FilterParameters>;
}

export default async function ScanReportsField(props: ScanReportsFieldProps) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const { id, tableId } = params;

  const defaultPageSize = 20;
  const defaultParams = {
    page_size: defaultPageSize,
  };
  const combinedParams = { ...defaultParams, ...searchParams };
  const query = objToQuery(combinedParams);
  const tableName = await getScanReportTable(id, tableId);
  const scanReportsFields = await getScanReportFieldsV3(id, tableId, query);
  const permissions = await getScanReportPermissions(id);

  // const scanReportsConcepts =
  //   scanReportsFields.results.length > 0
  //     ? await getAllScanReportConcepts(
  //         `object_id__in=${scanReportsFields.results
  //           .map((item) => item.id)
  //           .join(",")}`,
  //       )
  //     : [];

  // const conceptsFilter =
  //   scanReportsConcepts.length > 0
  //     ? await getAllConceptsFiltered(
  //         scanReportsConcepts?.map((item) => item.concept).join(","),
  //       )
  //     : [];

  const canEdit = permissions.permissions.includes("CanEdit") ||
  permissions.permissions.includes("CanAdmin");

  const filter = <ConceptDataFilter />;

  return (
    <div>
      <TableBreadcrumbs
        id={id}
        tableId={tableId}
        tableName={tableName.name}
        variant="table"
      />
      <div>
        <ConceptDataTableV3
          count={scanReportsFields.count}
          canEdit={canEdit}
          scanReportsData={scanReportsFields.results}
          defaultPageSize={defaultPageSize}
          columns={columns}
          tableId={tableId}
          scanReportId={id}
          Filter={filter}
        />
      </div>
    </div>
  );
}
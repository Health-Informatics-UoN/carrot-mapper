import { columns } from "./columns";
import {
  getScanReportFieldsV3,
  getScanReportPermissions,
  getScanReportTable,
} from "@/api/scanreports";
import { objToQuery } from "@/lib/client-utils";
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
  const [tableName, scanReportsFields, permissions] = await Promise.all([
    getScanReportTable(id, tableId),
    getScanReportFieldsV3(id, tableId, query),
    getScanReportPermissions(id),
  ]);

  const canEdit = permissions.permissions.includes("CanEdit") ||
  permissions.permissions.includes("CanAdmin");

  const filter = <ConceptDataFilter />;

  const breadcrumbs = await TableBreadcrumbs({
    id,
    tableId,
    tableName: tableName.name,
    variant: "table",
  });

  return (
    <div>
      {breadcrumbs}
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
import {
  getScanReportField,
  getScanReportPermissions,
  getScanReportTable,
  getScanReportValuesV3,
} from "@/api/scanreports";
import { objToQuery } from "@/lib/client-utils";
import { FilterParameters } from "@/types/filter";
import { columns } from "./columns";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { ConceptDataTableV3 } from "@/components/concepts/ConceptDataTableV3";
import { TableBreadcrumbs } from "@/components/scanreports/TableBreadcrumbs";

interface ScanReportsValueProps {
  params: Promise<{
    id: string;
    tableId: string;
    fieldId: string;
  }>;
  searchParams?: Promise<FilterParameters>;
}

export default async function ScanReportsValue(props: ScanReportsValueProps) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const { id, tableId, fieldId } = params;

  const defaultPageSize = 20;
  const defaultParams = {
    page_size: defaultPageSize,
  };
  const combinedParams = { ...defaultParams, ...searchParams };
  const query = objToQuery(combinedParams);
  const permissions = await getScanReportPermissions(id);
  const table = await getScanReportTable(id, tableId);
  const field = await getScanReportField(id, tableId, fieldId);
  const scanReportsValues = await getScanReportValuesV3(
    id,
    tableId,
    fieldId,
    query,
  );

  const canEdit =
    permissions.permissions.includes("CanEdit") ||
    permissions.permissions.includes("CanAdmin");

  return (
    <div>
      <TableBreadcrumbs
        id={id}
        tableId={tableId}
        fieldId={fieldId}
        tableName={table.name}
        fieldName={field.name}
        variant="field"
      />
      <div>
        <ConceptDataTableV3
          count={scanReportsValues.count}
          canEdit={canEdit}
          scanReportsData={scanReportsValues.results}
          defaultPageSize={defaultPageSize}
          columns={columns}
          filterCol="value"
          filterText="value "
          tableId={tableId}
        />
      </div>
    </div>
  );
}

import {
  getScanReportField,
  getScanReportPermissions,
  getScanReportTable,
  getScanReportValuesV3,
} from "@/api/scanreports";
import { objToQuery } from "@/lib/client-utils";
import { columns } from "./columns";
import { ConceptDataTableV3 } from "@/components/concepts/ConceptDataTableV3";
import { TableBreadcrumbs } from "@/components/scanreports/TableBreadcrumbs";
import { ConceptDataFilter } from "@/components/concepts/ConceptDataFilter";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

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
  const [permissions, table, field, scanReportsValues] = await Promise.all([
    getScanReportPermissions(id),
    getScanReportTable(id, tableId),
    getScanReportField(id, tableId, fieldId),
    getScanReportValuesV3(id, tableId, fieldId, query),
  ]);

  const filter = <ConceptDataFilter />;

  const canEdit =
    permissions.permissions.includes("CanEdit") ||
    permissions.permissions.includes("CanAdmin");

  const breadcrumbs = await TableBreadcrumbs({
    id,
    tableId,
    fieldId,
    tableName: table.name,
    fieldName: field.name,
    variant: "field",
  });

  return (
    <div>
      <div className="flex justify-between items-center">
        {breadcrumbs}
        <Button variant="link" asChild><Link href={`/scanreports/${id}/tables/${tableId}/fields/${fieldId}`}>Back to old experience <ArrowLeft className="text-carrot-brand" /></Link></Button>
      </div>
      <div>
        <ConceptDataTableV3
          count={scanReportsValues.count}
          canEdit={canEdit}
          scanReportsData={scanReportsValues.results}
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

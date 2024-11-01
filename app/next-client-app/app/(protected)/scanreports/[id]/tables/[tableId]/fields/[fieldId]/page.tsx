import {
  getScanReportField,
  getScanReportPermissions,
  getScanReportTable,
  getScanReportValues,
} from "@/api/scanreports";
import { objToQuery } from "@/lib/client-utils";
import { FilterParameters } from "@/types/filter";
import {
  getAllConceptsFiltered,
  getAllScanReportConcepts,
} from "@/api/concepts";
import { ConceptDataTable } from "@/components/concepts/ConceptDataTable";
import { columns } from "./columns";
import { Button } from "@/components/ui/button";
import Link from "next/link";

interface ScanReportsValueProps {
  params: {
    id: string;
    tableId: string;
    fieldId: string;
  };
  searchParams?: FilterParameters;
}

export default async function ScanReportsValue({
  params: { id, tableId, fieldId },
  searchParams,
}: ScanReportsValueProps) {
  const defaultPageSize = 20;
  const defaultParams = {
    page_size: defaultPageSize,
  };
  const combinedParams = { ...defaultParams, ...searchParams };
  const query = objToQuery(combinedParams);
  const permissions = await getScanReportPermissions(id);
  const table = await getScanReportTable(id, tableId);
  const field = await getScanReportField(id, tableId, fieldId);
  const scanReportsValues = await getScanReportValues(
    id,
    tableId,
    fieldId,
    query
  );

  const scanReportsConcepts =
    scanReportsValues.results.length > 0
      ? await getAllScanReportConcepts(
          `object_id__in=${scanReportsValues.results
            .map((item) => item.id)
            .join(",")}`
        )
      : [];
  const conceptsFilter =
    scanReportsConcepts.length > 0
      ? await getAllConceptsFiltered(
          scanReportsConcepts?.map((item) => item.concept).join(",")
        )
      : [];
  return (
    <div>
      <div className="gap-2 flex">
        {" "}
        <Link href={`/scanreports/${id}/tables/${tableId}`}>
          <Button variant={"secondary"} className="mb-3">
            Table: {table.name} {table.death_table && "(Death table)"}
          </Button>
        </Link>
        <Button variant={"secondary"} className="mb-3">
          Field: {field.name}
        </Button>
      </div>
      <div>
        <ConceptDataTable
          count={scanReportsValues.count}
          permissions={permissions}
          scanReportsConcepts={scanReportsConcepts}
          conceptsFilter={conceptsFilter}
          scanReportsData={scanReportsValues.results}
          defaultPageSize={defaultPageSize}
          columns={columns}
          clickable={false}
          filterCol="value"
          filterText="value "
          tableId={tableId}
        />
      </div>
    </div>
  );
}

import { columns } from "./columns";
import {
  getScanReportFields,
  getScanReportPermissions,
  getScanReportTable,
} from "@/api/scanreports";
import { objToQuery } from "@/lib/client-utils";
import { FilterParameters } from "@/types/filter";
import {
  getAllConceptsFiltered,
  getAllScanReportConcepts,
} from "@/api/concepts";
import { ConceptDataTable } from "@/components/concepts/ConceptDataTable";
import { Button } from "@/components/ui/button";

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

  const {
    id,
    tableId
  } = params;

  const defaultPageSize = 20;
  const defaultParams = {
    page_size: defaultPageSize,
  };
  const combinedParams = { ...defaultParams, ...searchParams };
  const query = objToQuery(combinedParams);
  const tableName = await getScanReportTable(id, tableId);
  const scanReportsFields = await getScanReportFields(id, tableId, query);
  const permissions = await getScanReportPermissions(id);

  const scanReportsConcepts =
    scanReportsFields.results.length > 0
      ? await getAllScanReportConcepts(
          `object_id__in=${scanReportsFields.results
            .map((item) => item.id)
            .join(",")}`,
        )
      : [];

  const conceptsFilter =
    scanReportsConcepts.length > 0
      ? await getAllConceptsFiltered(
          scanReportsConcepts?.map((item) => item.concept).join(","),
        )
      : [];

  return (
    <div>
      <Button variant={"secondary"} className="mb-3 bg-muted text-foreground-3">
        Table: {tableName.name}
      </Button>
      <div>
        <ConceptDataTable
          count={scanReportsFields.count}
          permissions={permissions}
          scanReportsConcepts={scanReportsConcepts}
          conceptsFilter={conceptsFilter}
          scanReportsData={scanReportsFields.results}
          defaultPageSize={defaultPageSize}
          columns={columns}
          filterCol="name"
          filterText="field "
          linkPrefix="fields/"
          tableId={tableId}
        />
      </div>
    </div>
  );
}

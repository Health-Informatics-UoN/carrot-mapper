import {
  getAllScanReportFields,
  getScanReportField,
  getScanReportPermissions,
  getScanReportTable
} from "@/api/scanreports";
import { objToQuery } from "@/lib/client-utils";
import { AlertCircleIcon } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { ScanReportTableUpdateForm } from "@/components/scanreports/ScanReportTableUpdateForm";
import { Button } from "@/components/ui/button";
import Link from "next/link";

interface UpdateTableProps {
  params: Promise<{
    id: string;
    tableId: string;
  }>;
}

export default async function UpdateTable(props: UpdateTableProps) {
  const params = await props.params;

  const { id, tableId } = params;

  const defaultPageSize = 50;
  const defaultParams = {
    fields: "name,id",
    page_size: defaultPageSize
  };
  const combinedParams = { ...defaultParams };
  const query = objToQuery(combinedParams);

  const scanReportsFields = await getAllScanReportFields(id, tableId, query);

  const table = await getScanReportTable(id, tableId);

  // Check if fields are available first before making the calls
  // Note: We create a fallback field object because the component expects ScanReportField,
  // not null. This is a temporary workaround until we improve the fetching pattern (#795)
  const fallbackField = {
    id: 0,
    name: "",
    created_at: new Date(),
    updated_at: new Date(),
    description_column: "",
    type_column: "",
    max_length: 0,
    nrows: 0,
    nrows_checked: 0,
    fraction_empty: "",
    nunique_values: 0,
    fraction_unique: "",
    ignore_column: null,
    is_patient_id: false,
    is_ignore: false,
    classification_system: null,
    pass_from_source: false,
    concept_id: 0,
    permissions: [],
    field_description: null,
    scan_report_table: 0
  };

  const personId = table.person_id?.id
    ? await getScanReportField(id, tableId, table.person_id.id)
    : fallbackField;
  const dateEvent = table.date_event?.id
    ? await getScanReportField(id, tableId, table.date_event.id)
    : fallbackField;
  const permissions = await getScanReportPermissions(id);

  return (
    <div>
      <Link href={`/scanreports/${id}/tables/${tableId}`}>
        <Button variant={"secondary"} className="mb-3">
          Update Table: {table.name}
        </Button>
      </Link>
      {(table.date_event === null || table.person_id === null) && (
        <Alert className="flex items-center gap-3 bg-accent text-accent-foreground mt-3 w-1/2">
          <div>
            <AlertCircleIcon />
          </div>
          <div>
            {" "}
            Mapping Rules cannot be generated without the Person ID and Date
            Event being set.
            <br />
            Once you set these, Mapping Rules will be generated for all Concepts
            currently associated to the table.
            <br />
          </div>
        </Alert>
      )}
      <div className="mt-1">
        <ScanReportTableUpdateForm
          scanreportFields={scanReportsFields}
          scanreportTable={table}
          permissions={permissions.permissions}
          personId={personId}
          dateEvent={dateEvent}
        />
      </div>
    </div>
  );
}

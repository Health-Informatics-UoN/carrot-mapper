import {
  getAllScanReportFields,
  getScanReportField,
  getScanReportPermissions,
  getScanReportTable,
} from "@/api/scanreports";
import { objToQuery } from "@/lib/client-utils";
import { AlertCircleIcon } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { ScanReportTableUpdateForm } from "@/components/scanreports/ScanReportTableUpdateForm";
import { Button } from "@/components/ui/button";
import Link from "next/link";

interface UpdateTableProps {
  params: {
    id: string;
    tableId: string;
  };
}

export default async function UpdateTable({
  params: { id, tableId },
}: UpdateTableProps) {
  const defaultPageSize = 50;
  const defaultParams = {
    fields: "name,id",
    page_size: defaultPageSize,
  };
  const combinedParams = { ...defaultParams };
  const query = objToQuery(combinedParams);

  const scanReportsFields = await getAllScanReportFields(id, tableId, query);

  const table = await getScanReportTable(id, tableId);
  const personId = await getScanReportField(id, tableId, table.person_id?.id);
  const dateEvent = await getScanReportField(id, tableId, table.date_event?.id);
  const permissions = await getScanReportPermissions(id);

  return (
    <div>
      <Link href={`/scanreports/${id}/tables/${tableId}`}>
        <Button variant={"secondary"} className="mb-3">
          Update Table: {table.name} {table.death_table && "(Death table)"}
        </Button>
      </Link>
      {(table.date_event === null || table.person_id === null) && (
        <Alert className="flex items-center gap-3 bg-carrot text-white mt-3 w-1/2">
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

import {
  getScanReport,
  getScanReportField,
  getScanReportPermissions,
  getScanReportTable,
} from "@/api/scanreports";
import { ScanReportFieldEditForm } from "@/components/scanreports/ScanReportFieldEditForm";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { notFound } from "next/navigation";

interface ScanReportsEditFieldProps {
  params: Promise<{
    id: string;
    tableId: string;
    fieldId: string;
  }>;
}

export default async function ScanReportsEditField(props: ScanReportsEditFieldProps) {
  const params = await props.params;

  const {
    id,
    tableId,
    fieldId
  } = params;

  const scanReport = await getScanReport(id);
  const table = await getScanReportTable(id, tableId);
  const field = await getScanReportField(id, tableId, fieldId);
  const permissions = await getScanReportPermissions(id);

  if (!scanReport) {
    return notFound();
  }

  return (
    <div>
      <div className="gap-2 flex">
        {" "}
        <Link href={`/scanreports/${id}/tables/${tableId}`}>
          <Button variant={"secondary"} className="mb-3">
            Table: {table.name}
          </Button>
        </Link>
        <Button variant={"secondary"} className="mb-3">
          Update Field: {field.name}
        </Button>
      </div>
      <div className="mt-2">
        <ScanReportFieldEditForm
          scanreportId={scanReport.id}
          scanReportField={field}
          permissions={permissions.permissions}
        />
      </div>
    </div>
  );
}

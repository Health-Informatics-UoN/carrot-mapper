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
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb";

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
      <Breadcrumb className="mb-3">
        <BreadcrumbList>
          <BreadcrumbItem>
            <Link href={`/scanreports/${id}`}>Tables</Link>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <Link href={`/scanreports/${id}/tables/${tableId}`}>Table: {table.name}</Link>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbPage>
            <Link href={`/scanreports/${id}/tables/${tableId}/fields/${fieldId}/update`}>Update Field: {field.name}</Link>
          </BreadcrumbPage>
        </BreadcrumbList>
      </Breadcrumb>
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

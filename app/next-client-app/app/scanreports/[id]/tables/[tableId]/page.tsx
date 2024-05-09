import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { columns } from "./columns";
import { getScanReport, getScanReportFields } from "@/api/scanreports";
import { DataTable } from "@/components/data-table";
import { objToQuery } from "@/lib/client-utils";

type Props = {
  params: {
    id: string;
    tableId: string;
  };
  searchParams?: FilterParameters;
};

export default async function ScanReportsField({
  params: { id, tableId },
  searchParams,
}: Props) {
  const defaultParams = {
    scan_report_table: tableId,
  };

  const combinedParams = { ...defaultParams, ...searchParams };

  const query = objToQuery(combinedParams);
  const scanReportsTables = await getScanReportFields(query);
  const scanReportsName = await getScanReport(id);
  return (
    <div className="pt-10 px-16">
      <div>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="/">Home</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>/</BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbLink href="/scanreports">Scan Reports</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>/</BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbLink href={`/scanreports/${id}`}>
                {scanReportsName.dataset}
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>/</BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbLink href={`/scanreports/${id}/tables/${tableId}`}>
                {tableId}
              </BreadcrumbLink>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>
      <div className="mt-3">
        <h1 className="text-4xl font-semibold">Fields</h1>
      </div>
      <div className="flex justify-between mt-3 flex-col sm:flex-row">
        <div className="flex gap-2">
          <Link href="/">
            <Button size="lg" className="text-md">
              Scan Report Details
            </Button>
          </Link>
          <Link href="/">
            <Button size="lg" className="text-md">
              Rules
            </Button>
          </Link>
        </div>
      </div>
      <div>
        <DataTable
          columns={columns}
          data={scanReportsTables.results}
          count={scanReportsTables.count}
          filter="name"
          linkPrefix="/tables/"
        />
      </div>
    </div>
  );
}

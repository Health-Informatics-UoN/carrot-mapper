import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbSeparator, BreadcrumbPage } from "@/components/ui/breadcrumb";
import Link from "next/link";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ChevronDownIcon } from "lucide-react";
import { getScanReportTables } from "@/api/scanreports";

interface TableBreadcrumbsProps {
  id: string;
  tableId?: string;
  fieldId?: string;
  tableName?: string;
  fieldName?: string;
  variant: "table" | "field" | "fieldUpdate";
}

export async function TableBreadcrumbs({
  id,
  tableId,
  fieldId,
  tableName,
  fieldName,
  variant,
}: TableBreadcrumbsProps) {

  const tables = await getScanReportTables(id, undefined);

  return (
    <Breadcrumb className="mb-3">
      <BreadcrumbList>
        <BreadcrumbItem>
          <Link href={`/scanreports/${id}`}>Tables</Link>
        </BreadcrumbItem>
        {variant === "table" && tableId && tableName && (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbPage>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <span className="flex items-center gap-1">
                    <Link href={`/scanreports/${id}/tables/${tableId}`}>Table: {tableName}</Link>
                    <ChevronDownIcon size={16} />
                  </span>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                  {tables.results.map((table) => (
                    <DropdownMenuItem key={table.id}>
                      <Link href={`/scanreports/${id}/tables/${table.id}`}>{table.name}</Link>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </BreadcrumbPage>
          </>
        )}
        {variant === "field" && tableId && tableName && fieldId && fieldName && (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <span className="flex items-center gap-1">
                    <Link href={`/scanreports/${id}/tables/${tableId}`}>Table: {tableName}</Link>
                    <ChevronDownIcon size={16} />
                  </span>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                  {tables.results.map((table) => (
                    <DropdownMenuItem key={table.id}>
                      <Link href={`/scanreports/${id}/tables/${table.id}`}>{table.name}</Link>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbPage>
              <Link href={`/scanreports/${id}/tables/${tableId}/fields/${fieldId}`}>Field: {fieldName}</Link>
            </BreadcrumbPage>
          </>
        )}
        {variant === "fieldUpdate" && tableId && tableName && fieldId && fieldName && (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <Link href={`/scanreports/${id}/tables/${tableId}`}>Table: {tableName}</Link>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbPage>
              <Link href={`/scanreports/${id}/tables/${tableId}/fields/${fieldId}/update`}>Update Field: {fieldName}</Link>
            </BreadcrumbPage>
          </>
        )}
      </BreadcrumbList>
    </Breadcrumb>
  );
} 
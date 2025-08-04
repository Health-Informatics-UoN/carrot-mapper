import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbSeparator, BreadcrumbPage } from "@/components/ui/breadcrumb";
import Link from "next/link";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ChevronDownIcon } from "lucide-react";
import { getScanReportFields, getScanReportTables } from "@/api/scanreports";

interface TableBreadcrumbsProps {
  id: string;
  tableId?: string;
  fieldId?: string;
  tableName?: string;
  fieldName?: string;
  variant: "table" | "field" | "fieldUpdate";
}

// Helper: Table breadcrumb with dropdown
function TableBreadcrumbWithDropdown({ id, tableId, tableName, tables }: { id: string, tableId: string, tableName: string, tables: any }) {
  return (
    <span className="flex items-center gap-1">
      <Link href={`/scanreports/${id}/tables/${tableId}`}>Table: {tableName}</Link>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <span tabIndex={0} role="button" aria-label="Show table list">
            <ChevronDownIcon size={16} />
          </span>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          {tables.results.map((table: any) => (
            <DropdownMenuItem asChild key={table.id}>
              <Link href={`/scanreports/${id}/tables/${table.id}`}>{table.name}</Link>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </span>
  );
}

// Helper: Field breadcrumb with dropdown
function FieldBreadcrumbWithDropdown({ id, tableId, fieldId, fieldName, fields }: { id: string, tableId: string, fieldId: string, fieldName: string, fields: any }) {
  return (
    <span className="flex items-center gap-1">
      <Link href={`/scanreports/${id}/tables/${tableId}/fields/${fieldId}`}>Field: {fieldName}</Link>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <span tabIndex={0} role="button" aria-label="Show field list">
            <ChevronDownIcon size={16} />
          </span>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          {fields.results.map((field: any) => (
            <DropdownMenuItem asChild key={field.id}>
              <Link href={`/scanreports/${id}/tables/${tableId}/fields/${field.id}`}>{field.name}</Link>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </span>
  );
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
  let fields: any = { count: 0, next: null, previous: null, results: [] };
  if (tableId) {
    fields = await getScanReportFields(id, tableId, undefined);
  }

  return (
    <Breadcrumb className="mb-3 hidden md:block">
      <BreadcrumbList>
        <BreadcrumbItem>
          <Link href={`/scanreports/${id}`}>Tables</Link>
        </BreadcrumbItem>
        {variant === "table" && tableId && tableName && (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbPage>
              <TableBreadcrumbWithDropdown id={id} tableId={tableId} tableName={tableName} tables={tables} />
            </BreadcrumbPage>
          </>
        )}
        {variant === "field" && tableId && tableName && fieldId && fieldName && (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <TableBreadcrumbWithDropdown id={id} tableId={tableId} tableName={tableName} tables={tables} />
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbPage>
              <FieldBreadcrumbWithDropdown id={id} tableId={tableId} fieldId={fieldId} fieldName={fieldName} fields={fields} />
            </BreadcrumbPage>
          </>
        )}
        {variant === "fieldUpdate" && tableId && tableName && fieldId && fieldName && (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <TableBreadcrumbWithDropdown id={id} tableId={tableId} tableName={tableName} tables={tables} />
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
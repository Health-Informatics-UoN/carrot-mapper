import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbSeparator, BreadcrumbPage } from "@/components/ui/breadcrumb";
import Link from "next/link";

interface TableBreadcrumbsProps {
  id: string;
  tableId?: string;
  fieldId?: string;
  tableName?: string;
  fieldName?: string;
  variant: "table" | "field" | "fieldUpdate";
}

export function TableBreadcrumbs({
  id,
  tableId,
  fieldId,
  tableName,
  fieldName,
  variant,
}: TableBreadcrumbsProps) {
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
              <Link href={`/scanreports/${id}/tables/${tableId}`}>Table: {tableName}</Link>
            </BreadcrumbPage>
          </>
        )}
        {variant === "field" && tableId && tableName && fieldId && fieldName && (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <Link href={`/scanreports/${id}/tables/${tableId}`}>Table: {tableName}</Link>
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
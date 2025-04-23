"use client";

import {
  ColumnDef,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  useReactTable,
} from "@tanstack/react-table";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import React from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import { DataTablePagination } from "./DataTablePagination";
import { Columns3 } from "lucide-react";

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  count: number;
  linkPrefix?: string;
  Filter?: JSX.Element;
  viewColumns?: boolean;
  paginated?: boolean;
  overflow?: boolean;
  RefreshButton?: JSX.Element;
  defaultPageSize?: 10 | 20 | 30 | 40 | 50;
  isUploading?: boolean; // New prop
}

function UrlBuilder(id: string, prefix: string = "") {
  return `${prefix}${id}/`;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  count,
  linkPrefix = "",
  Filter,
  viewColumns = true,
  paginated = true,
  overflow = true,
  RefreshButton,
  defaultPageSize,
  isUploading = false, // Default to false
}: DataTableProps<TData, TValue>) {
  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>({});

  const table = useReactTable({
    data,
    columns,
    manualPagination: true,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    manualFiltering: true,
    manualSorting: true,
    onColumnVisibilityChange: setColumnVisibility,
    state: {
      columnVisibility,
    },
  });

  const handleRowClick = (id: string) => {
    let location = window.location.pathname;
    if (/datasets\/\d+/.test(location)) {
      location = "/scanreports/";
    }
    if (/projects\/\d+/.test(location)) {
      location = "/datasets/";
    }
    window.location.href = UrlBuilder(
      id,
      `${location.endsWith("/") ? location : location + "/"}${linkPrefix}`
    );
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-3">
        {Filter}
        {RefreshButton}
        {viewColumns && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                aria-label="Toggle columns"
                variant="outline"
                className="ml-auto hidden lg:flex"
              >
                <Columns3 className="mr-2 size-4" />
                Columns
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {table
                .getAllColumns()
                .filter((column) => column.getCanHide())
                .map((column) => {
                  return (
                    <DropdownMenuCheckboxItem
                      key={column.id}
                      className="capitalize"
                      checked={column.getIsVisible()}
                      onCheckedChange={(value) =>
                        column.toggleVisibility(!!value)
                      }
                    >
                      {column.id}
                    </DropdownMenuCheckboxItem>
                  );
                })}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      <div className="rounded-md border">
        <Table overflow={overflow}>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>

          <TableBody>
            {data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  {isUploading
                    ? "Upload is in progress and scan report data will be available soon."
                    : "No results."}
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  onClick={() => handleRowClick(row.original["id"])}
                  className="cursor-pointer"
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {paginated && (
        <DataTablePagination table={table} totalCount={count} />
      )}
    </div>
  );
}

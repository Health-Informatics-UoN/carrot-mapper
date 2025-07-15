"use client";

import {
  ColumnDef,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  useReactTable
} from "@tanstack/react-table";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import React from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
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
  defaultPageSize
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
      columnVisibility
    }
  });

  const handleRowClick = (id: string) => {
    let location = window.location.pathname;
    // the test method of the regular expression object to check if location contains "datasets/" followed by one or more digits.
    // If it does, it sets location to "/scanreports/"
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
        {/* Views Columns Menu */}
        {viewColumns && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                aria-label="Toggle columns"
                variant="outline"
                className="ml-auto hidden lg:flex transition-colors"
              >
                <Columns3 />
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
        <Table overflow={overflow.toString()}>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow
                key={headerGroup.id}
                className="group transition-colors"
              >
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className="transition-colors cursor-pointer"
                  >
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext()
                    )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                  className="transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      <div>
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </div>
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center"
                >
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      {paginated && (
        <div className="flex items-center justify-center space-x-2 pt-4">
          <DataTablePagination
            count={count}
            defaultPageSize={defaultPageSize}
          />
        </div>
      )}
    </div>
  );
}

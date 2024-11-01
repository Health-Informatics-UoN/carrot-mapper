"use client";

import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { EditButton } from "@/components/scanreports/EditButton";
import { Tooltips } from "@/components/Tooltips";

export const columns: ColumnDef<ScanReportTable>[] = [
  {
    id: "Name",
    accessorKey: "name",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Name" sortName="name" />
    ),
    enableHiding: true,
    enableSorting: true,
  },
  {
    id: "Person ID",
    accessorKey: "person_id",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Person ID"
        sortName="person_id"
      />
    ),
    cell: ({ row }) => {
      const { person_id } = row.original;
      return <>{person_id?.name}</>;
    },
    enableHiding: true,
    enableSorting: false,
  },
  {
    id: "Event Date",
    accessorKey: "date_event",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Date Event"
        sortName="date_event"
      />
    ),
    cell: ({ row }) => {
      const { date_event } = row.original;
      return <>{date_event?.name}</>;
    },
    enableHiding: true,
    enableSorting: false,
  },
  {
    id: "note",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Note" />
    ),
    cell: ({ row }) => {
      const { death_table } = row.original;
      return (
        <div>
          {death_table && (
            <h3 className="flex">
              {" "}
              Death table
              <Tooltips
                content={
                  <h2>
                    Concepts added to this table with domains{" "}
                    <span className="font-bold">
                      Race, Ethnicity and Gender
                    </span>{" "}
                    will be mapped to the{" "}
                    <span className="font-bold">Person</span> table. Concepts
                    with <span className="font-bold">other domains</span> will
                    be mapped to the <span className="font-bold">Death</span>{" "}
                    table.
                  </h2>
                }
              />
            </h3>
          )}
        </div>
      );
    },
  },
  {
    id: "edit",
    header: ({ column }) => <DataTableColumnHeader column={column} title="" />,
    cell: ({ row }) => {
      const { id, scan_report, permissions } = row.original;
      return (
        <EditButton
          scanreportId={scan_report}
          tableId={id}
          type="table"
          permissions={permissions}
        />
      );
    },
  },
];

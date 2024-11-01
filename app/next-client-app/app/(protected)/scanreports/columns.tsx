"use client";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Pencil2Icon,
  DotsHorizontalIcon,
  EyeNoneIcon,
  EyeOpenIcon,
  TrashIcon,
} from "@radix-ui/react-icons";
import Link from "next/link";
import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { Button } from "@/components/ui/button";
import { UploadStatus } from "@/components/scanreports/UploadStatus";
import { format } from "date-fns/format";
import { HandleArchive } from "@/components/HandleArchive";
import { useState } from "react";
import DeleteDialog from "@/components/scanreports/DeleteDialog";
import { MappingStatus } from "@/components/scanreports/MappingStatus";

export const columns: ColumnDef<ScanReport>[] = [
  {
    id: "id",
    accessorKey: "id",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="id" sortName="id" />
    ),
    enableHiding: true,
  },
  {
    id: "Name",
    accessorKey: "dataset",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Name" sortName="dataset" />
    ),
    enableHiding: true,
  },
  {
    id: "Dataset",
    accessorKey: "parent_dataset.name",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Dataset"
        sortName="parent_dataset"
      />
    ),
    enableHiding: true,
  },
  {
    id: "Data Partner",
    accessorKey: "data_partner",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Data Partner" />
    ),
    enableHiding: true,
    enableSorting: false,
  },
  {
    id: "Author",
    accessorKey: "author.username",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Author" />
    ),
    enableHiding: true,
    enableSorting: true,
  },
  {
    id: "Uploaded",
    accessorKey: "created_at",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Uploaded"
        sortName="created_at"
      />
    ),
    enableHiding: false,
    enableSorting: true,
    cell: ({ row }) => {
      const date = new Date(row.original.created_at);
      return format(date, "MMM dd, yyyy h:mm a");
    },
  },
  {
    id: "Upload Status",
    accessorKey: "upload_status",
    header: () => <div className="text-center"> Upload Status</div>,
    enableHiding: true,
    enableSorting: false,
    cell: ({ row }) => {
      const { upload_status } = row.original;
      return (
        <UploadStatus
          upload_status={upload_status || { value: "IN_PROGRESS" }}
        />
      );
    },
  },
  {
    id: "Mapping Status",
    header: () => <div className="text-center"> Mapping Status</div>,
    enableHiding: true,
    enableSorting: false,
    cell: ({ row }) => {
      const { id, mapping_status, upload_status, dataset } = row.original;
      const upload_status_check = upload_status ?? { value: "IN_PROGRESS" };
      return (
        <div className="flex justify-center text-center">
          <MappingStatus
            id={id.toString()}
            mapping_status={mapping_status || { value: "PENDING" }}
            dataset={dataset}
            className="w-[180px]"
            disabled={upload_status_check.value === "COMPLETE" ? false : true} // Users who don't have permissions will see the error
          />
        </div>
      );
    },
  },
  {
    id: "Actions",
    header: "Actions",
    enableHiding: false,
    cell: ({ row }) => {
      const { id, hidden, dataset } = row.original;
      const [isOpen, setOpen] = useState<boolean>(false);

      return (
        <>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                <DotsHorizontalIcon className="size-4" aria-hidden="true" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <Link href={`/scanreports/${id}/details/`} prefetch={false}>
                <DropdownMenuItem>
                  Details <Pencil2Icon className="ml-auto" />
                </DropdownMenuItem>
              </Link>
              <DropdownMenuItem
                onClick={() =>
                  HandleArchive({
                    id: id,
                    hidden: hidden,
                    ObjName: dataset,
                    type: "scanreports",
                  })
                }
              >
                {hidden ? "Unarchive" : "Archive"}
                {hidden ? (
                  <EyeOpenIcon className="ml-auto" />
                ) : (
                  <EyeNoneIcon className="ml-auto" />
                )}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setOpen(true)}
                className="text-red-400"
              >
                Delete <TrashIcon className="ml-auto" />
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <DeleteDialog id={id} isOpen={isOpen} setOpen={setOpen} />
        </>
      );
    },
  },
];

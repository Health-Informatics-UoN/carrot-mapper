"use client";

import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/data-table/DataTableColumnHeader";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { format } from "date-fns/format";
import { formatDistanceToNow } from "date-fns/formatDistanceToNow";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { saveAs } from "file-saver";
import { Badge } from "@/components/ui/badge";
import { downloadFile } from "@/api/files";
import { toast } from "sonner";

export const columns: ColumnDef<FileDownload>[] = [
  {
    id: "Created",
    accessorKey: "created_at",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Created"
        sortName="created_at"
      />
    ),
    cell: ({ row }) => {
      const { created_at } = row.original;
      return (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <>{formatDistanceToNow(created_at)} ago</>
            </TooltipTrigger>
            <TooltipContent>
              {format(created_at, "MMM dd, yyyy h:mm a")}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    },
    enableHiding: true,
    enableSorting: true,
  },
  {
    id: "User",
    accessorKey: "user",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="Generated By"
        sortName="user"
      />
    ),
    cell: ({ row }) => {
      const { user } = row.original;
      return <>{user.username}</>;
    },
    enableHiding: true,
    enableSorting: false,
  },
  {
    id: "Type",
    accessorKey: "file_type",
    header: ({ column }) => (
      <DataTableColumnHeader
        column={column}
        title="File Type"
        sortName="file_type"
      />
    ),
    cell: ({ row }) => {
      const { file_type } = row.original;
      return <Badge variant="outline">{file_type.display_name}</Badge>;
    },
    enableHiding: true,
    enableSorting: false,
  },
  {
    id: "Download",
    header: ({ column }) => <DataTableColumnHeader column={column} title="" />,
    cell: ({ row }) => {
      const { id, scan_report, file_type, name } = row.original;
      const handleDownload = async () => {
        const response = await downloadFile(scan_report, file_type.value, id);
        if (response.success) {
          // Based on the file type to process the data from the response accordingly
          if (file_type.value == "mapping_json") {
            const blob = new Blob([JSON.stringify(response.data)], {
              type: "application/json",
            });
            saveAs(blob, name);
          } else if (file_type.value == "mapping_csv") {
            const blob = new Blob([response.data], {
              type: "text/csv",
            });
            saveAs(blob, name);
          }
        } else {
          toast.error(
            `Error downloading file: ${(response.errorMessage as any).message}`
          );
        }
      };
      return (
        <Button variant={"outline"} onClick={handleDownload}>
          Download <Download />
        </Button>
      );
    },
    enableHiding: true,
    enableSorting: false,
  },
];

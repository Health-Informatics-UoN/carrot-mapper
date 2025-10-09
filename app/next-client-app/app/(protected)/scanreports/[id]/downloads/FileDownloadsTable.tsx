"use client";

import { useState, useMemo } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Eye, EyeOff } from "lucide-react";
import { FILE_RETENTION_DAYS } from "@/constants/config";

interface FileDownloadsTableProps {
  data: FileDownload[];
  count: number;
  columns: ColumnDef<FileDownload>[];
  Filter?: JSX.Element;
  defaultPageSize: 10 | 20 | 30 | 40 | 50;
}

export function FileDownloadsTable({
  data,
  count,
  columns,
  Filter,
  defaultPageSize
}: FileDownloadsTableProps) {
  const [showOldFiles, setShowOldFiles] = useState(false);

  const cutoffDate = useMemo(() => {
    const millisecondsPerDay = 24 * 60 * 60 * 1000;
    return new Date(Date.now() - FILE_RETENTION_DAYS * millisecondsPerDay);
  }, []);

  const { recentFiles, oldFiles } = useMemo(() => {
    const recent: FileDownload[] = [];
    const old: FileDownload[] = [];

    data.forEach((file) => {
      const fileDate = new Date(file.created_at);
      if (fileDate >= cutoffDate) {
        recent.push(file);
      } else {
        old.push(file);
      }
    });

    return { recentFiles: recent, oldFiles: old };
  }, [data, cutoffDate]);

  const displayedFiles = showOldFiles ? data : recentFiles;
  const displayedCount = showOldFiles ? count : recentFiles.length;

  const filterComponent = (
    <div className="flex gap-2 items-center">
      {Filter}
      {oldFiles.length > 0 && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowOldFiles(!showOldFiles)}
          className="ml-auto"
        >
          {showOldFiles ? (
            <>
              <EyeOff className="mr-2 h-4 w-4" />
              Hide older files
            </>
          ) : (
            <>
              <Eye className="mr-2 h-4 w-4" />
              Show {oldFiles.length} older file
              {oldFiles.length !== 1 ? "s" : ""}
            </>
          )}
        </Button>
      )}
    </div>
  );

  return (
    <DataTable
      columns={columns}
      data={displayedFiles}
      count={displayedCount}
      Filter={filterComponent}
      defaultPageSize={defaultPageSize}
    />
  );
}

"use client";

import { downloadFile } from "@/api/files";
import { toast } from "sonner";
import { saveAs } from "file-saver";
import { HardDriveDownload } from "lucide-react";
import { convertBase64toBlob } from "@/lib/client-utils";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";

interface ExportProps {
  scanReportId: string;
  scanReportName: string;
}

const ExportScanReport = ({ scanReportId, scanReportName }: ExportProps) => {
  const handleDownload = async () => {
    const response = await downloadFile(Number(scanReportId));
    if (response.success) {
      // Convert back Base64 to Blob
      const blobArray = convertBase64toBlob(response.data);
      const blob = new Blob([blobArray], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      });
      saveAs(blob, `${scanReportName.replace(/[^a-zA-Z0-9]/g, "_")}.xlsx`);
    } else {
      toast.error(
        `Error exporting Scan report: ${(response.errorMessage as any).message}`
      );
    }
  };
  return (
    <DropdownMenuItem onSelect={handleDownload}>
      <HardDriveDownload className="mr-2 size-4" />
      Export
    </DropdownMenuItem>
  );
};

export default ExportScanReport;

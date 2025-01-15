"use client";

import { downloadFile } from "@/api/files";
import { toast } from "sonner";
import { saveAs } from "file-saver";
import { Download } from "lucide-react";
import { convertBase64toBlob } from "@/lib/client-utils";

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
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      saveAs(blob, `${scanReportName.replace(/[^a-zA-Z0-9]/g, "_")}.xlsx`);
    } else {
      toast.error(
        `Error exporting Scan report: ${(response.errorMessage as any).message}`
      );
    }
  };
  return (
    <div
      role="button"
      onClick={handleDownload}
      className="hover:bg-carrot-200 relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors focus:bg-carrot-100 focus:text-carrot-900 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 dark:focus:bg-carrot-800 dark:focus:text-carrot-50"
    >
      <Download className="mr-2 size-4" />
      Export Scan Report
    </div>
  );
};

export default ExportScanReport;

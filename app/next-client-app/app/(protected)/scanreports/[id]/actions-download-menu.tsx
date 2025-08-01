"use client";

import {
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuGroup
} from "@/components/ui/dropdown-menu";
import { FileJson, FileSpreadsheet } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { requestFile } from "@/api/files";

type Props = { scanreportId: string };

export function ActionsDownloadMenu({ scanreportId }: Props) {
  const router = useRouter();

  const handleDownload = async (fileType: FileTypeFormat) => {
    const resp = await requestFile(Number(scanreportId), fileType);
    if (resp.success) {
      router.push(`/scanreports/${scanreportId}/downloads`);
      toast.success("File requested.");
    } else {
      toast.error(
        `Error downloading file: ${(resp.errorMessage as any).message}`
      );
    }
  };

  return (
    <DropdownMenuGroup>
      <DropdownMenuLabel>Downloads</DropdownMenuLabel>
      <DropdownMenuItem onSelect={() => handleDownload("application/json")}>
        <FileJson />
        Mapping JSON
      </DropdownMenuItem>
      <DropdownMenuItem onSelect={() => handleDownload("text/csv")}>
        <FileSpreadsheet />
        Mapping CSV
      </DropdownMenuItem>
    </DropdownMenuGroup>
  );
}

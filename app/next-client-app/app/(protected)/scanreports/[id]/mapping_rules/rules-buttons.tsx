"use client";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import {
  BarChartHorizontalBig,
  ChevronDown,
  FileJson,
  FileSpreadsheet,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { GetFile } from "@/app/(protected)/scanreports/[id]/mapping_rules/get-file";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { requestFile } from "@/api/files";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

export function RulesButton({
  scanreportId,
  query,
  filename,
}: {
  scanreportId: string;
  query: string;
  filename: string;
}) {
  const router = useRouter();

  const handleDownload = async (fileType: FileTypeFormat) => {
    const resp = await requestFile(Number(scanreportId), fileType);
    console.log("RESPONSE",resp);
    if (resp.success) {
      router.push(`downloads`);
      toast.success("File requested.");
    } else {
      toast.error(
        `Error downloading file: ${(resp.errorMessage as any).message}`
      );
    }
  };
  return (
    <div className="hidden md:flex gap-2 justify-end w-full mr-2">
      <div>
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline">
              View Map Diagram
              <BarChartHorizontalBig className="ml-2 size-4" />
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-[1200px]">
            <ScrollArea className="w-auto h-[400px]">
              <GetFile
                name="Download Map Diagram"
                filename={filename}
                scanreportId={scanreportId}
                query={query}
                variant="diagram"
                type="image/svg+xml"
              />
            </ScrollArea>
          </DialogContent>
        </Dialog>
      </div>
      <div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline">
              Request Download <ChevronDown className="ml-2 size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-[180px]">
            <DropdownMenuItem>
              <Button
                onClick={() => handleDownload("application/json")}
                variant={"ghost"}
                size={"sm"}
              >
                Mapping JSON
                <FileJson className="ml-2 size-4" />
              </Button>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Button
                onClick={() => handleDownload("text/csv")}
                variant={"ghost"}
                size={"sm"}
              >
                Mapping CSV
                <FileSpreadsheet className="ml-2 size-4" />
              </Button>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

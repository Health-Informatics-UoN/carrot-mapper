"use client";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { BarChartHorizontalBig } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { GetFile } from "@/app/(protected)/scanreports/[id]/mapping_rules/get-file";

export function RulesButton({
  scanreportId,
  query,
  filename,
}: {
  scanreportId: string;
  query: string;
  filename: string;
}) {
 
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
    </div>
  );
}

"use client";

import { useState } from "react";
import { CloudUpload } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { PublishToRegistryForm } from "./PublishToRegistryForm";


/* ---- Interface ---- */

interface Props {
  scanReportId: string;
  scanReportName: string;
  lastPublishedVersion?: string | null;
}

/**
 * Dialog for publishing a Scan Report's mapping set to the Registry.
 *
 * Displays the Scan Report details and renders the publishing form,
 * allowing users to configure the mapping set metadata.
 */

export function PublishToRegistryDialog({
  scanReportId,
  scanReportName,
  lastPublishedVersion,
}: Props) {

  // Dialog open or closed State.

  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button type="button" variant="outline" className="text-foreground">
          <CloudUpload className="size-4" />
          Publish to Registry
        </Button>
      </DialogTrigger>

      {/* Responsive dialog with a right-to-centre opening animation. */}
      <DialogContent
        className="
          max-h-[calc(100svh-2rem)] max-w-[calc(100%-2rem)] sm:max-w-xl
          data-[state=open]:slide-in-from-right-full
          data-[state=closed]:slide-out-to-right-full
        "
      >

        {/* Display the dialog title and selected Scan Report details. */}
        <DialogHeader className="border-b border-border pb-5 text-left">
          <DialogTitle className="flex items-center gap-2">
            <CloudUpload className="size-5" />
            Publish to Registry
          </DialogTitle>

          <DialogDescription className="wrap=break-words pt-2 text-sm">
            <span className="mb-1 flex flex-wrap items-baseline gap-x-3">
              <span>Scan Report Name: <strong className="font-semibold text-foreground">{scanReportName}</strong></span>
              <span><span aria-hidden="true" className="mr-3 hidden sm:inline">|</span>ID: <strong className="font-semibold text-foreground">{scanReportId}</strong></span>
            </span>
            Publish a mapping set to the Carrot Mappings Registry.
          </DialogDescription>

        </DialogHeader>


        {/* Remounting on open resets unsaved form state for each session. */}
        {open && (
          <PublishToRegistryForm
            scanReportId={scanReportId}
            lastPublishedVersion={lastPublishedVersion}
            onCancel={() => setOpen(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

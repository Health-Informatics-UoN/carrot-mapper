"use client";

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { updateScanReportTable } from "@/api/scanreports";
import { useRouter } from "next/navigation";

interface DeathTableConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  scanReportId: number;
  tableId: number;
  tableName: string;
  isDeathTable: boolean;
  onSuccess?: () => void;
}

export function DeathTableConfirmDialog({
  open,
  onOpenChange,
  scanReportId,
  tableId,
  tableName,
  isDeathTable,
  onSuccess,
}: DeathTableConfirmDialogProps) {
  const router = useRouter();
  const markingAsDeath = !isDeathTable;

  const handleConfirm = async () => {
    const response = await updateScanReportTable(
      scanReportId,
      tableId,
      { death_table: markingAsDeath },
    );
    if (response) {
      toast.error(
        `Failed to update DEATH table setting: ${response.errorMessage}`,
      );
    } else {
      toast.success(
        markingAsDeath
          ? "Table marked as DEATH table successfully."
          : "Table unmarked as DEATH table successfully.",
      );
      onOpenChange(false);
      onSuccess?.();
      router.refresh();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader className="text-start">
          <DialogTitle>
            {markingAsDeath ? "Mark as DEATH table" : "Unmark as DEATH table"}
          </DialogTitle>
          <DialogDescription>
            {markingAsDeath ? (
              <>
                Are you sure you want to mark &quot;{tableName}&quot; as a
                DEATH table? This will enable auto-mapping as a death table for
                any death SR uploads.
              </>
            ) : (
              <>
                Are you sure you want to unmark &quot;{tableName}&quot; as a
                DEATH table? Auto-mapping as a death table will no longer apply
                to this table.
              </>
            )}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="flex-col space-y-2 sm:space-y-0 sm:space-x-2">
          <Button onClick={handleConfirm}>
            {markingAsDeath ? "Mark as DEATH table" : "Unmark"}
          </Button>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

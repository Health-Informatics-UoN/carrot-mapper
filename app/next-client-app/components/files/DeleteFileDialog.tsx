"use client";

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "../ui/dialog";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { deleteFile } from "@/api/files";
import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
import { useState } from "react";

interface DeleteFileDialogProps {
  fileId: number;
  scanReportId: number;
  fileName: string;
  isOpen?: boolean;
  setOpen?: (isOpen: boolean) => void;
  needTrigger?: boolean;
}

const DeleteFileDialog = ({
  fileId,
  scanReportId,
  fileName,
  isOpen,
  setOpen,
  needTrigger = false
}: DeleteFileDialogProps) => {
  const router = useRouter();
  const [internalOpen, setInternalOpen] = useState(false);
  const dialogOpen = isOpen !== undefined ? isOpen : internalOpen;
  const setDialogOpen = setOpen || setInternalOpen;

  const handleDelete = async () => {
    const response = await deleteFile(scanReportId, fileId);
    if (response.success) {
      toast.success(`File "${fileName}" deleted successfully`);
      router.refresh();
      setDialogOpen(false); // This will close dialog after successful deletion
    } else {
      toast.error(
        `Failed to delete file: ${response.errorMessage || "Unknown error"}`
      );
    }
  };

  return (
    <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
      {needTrigger && (
        <DialogTrigger asChild>
          <Button variant="destructive" size="sm">
            <Trash2 className="h-4 w-4" />
          </Button>
        </DialogTrigger>
      )}
      <DialogContent>
        <DialogHeader className="text-start">
          <DialogTitle>Delete File</DialogTitle>
        </DialogHeader>
        <p className="text-sm">
          Are you sure you want to delete "{fileName}"? This action cannot be
          undone and will permanently remove the file from storage.
        </p>
        <DialogFooter className="flex-col space-y-2 sm:space-y-0 sm:space-x-2">
          <Button variant="destructive" onClick={handleDelete}>
            Delete
          </Button>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default DeleteFileDialog;

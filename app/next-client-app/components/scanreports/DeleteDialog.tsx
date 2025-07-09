"use client";
import React, { useState } from "react";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "../ui/dialog";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { deleteScanReport } from "@/api/scanreports";
import { useRouter } from "next/navigation";
import { TrashIcon } from "lucide-react";
import { DropdownMenuItem } from "../ui/dropdown-menu";

interface DeleteDialogProps {
  id: number;
  redirect?: boolean;
  isOpen?: boolean;
  setOpen?: (isOpen: boolean) => void;
  needTrigger?: boolean;
}

const DeleteDialog = ({
  id,
  redirect = false,
  isOpen: controlledOpen,
  setOpen: setControlledOpen,
  needTrigger = false
}: DeleteDialogProps) => {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  const handleDelete = async () => {
    const response = await deleteScanReport(id);
    if (response) {
      toast.error(`Failed to delete the Scan Report: ${response.errorMessage}`);
    } else {
      toast.success("Scan Report successfully deleted");
    }
    setOpen(false);
    if (setControlledOpen) setControlledOpen(false);
    if (redirect) router.push("/scanreports/");
  };

  const dialogOpen = controlledOpen !== undefined ? controlledOpen : open;
  const setDialogOpen = setControlledOpen || setOpen;

  return (
    <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
      {needTrigger && (
        <DropdownMenuItem
          className="
            group
            text-black dark:text-white
            hover:!text-destructive focus:!text-destructive
            transition-colors
          "
          onSelect={(e) => {
            e.preventDefault();
            setDialogOpen(true);
          }}
        >
          <TrashIcon className="mr-2 size-4 group-hover:text-destructive transition-colors" />
          Delete
        </DropdownMenuItem>
      )}
      <DialogContent>
        <DialogHeader className="text-start">
          <DialogTitle>Delete Scan Report</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete this Scan Report? This will:
          </DialogDescription>
          <ul className="text-muted-foreground list-disc pl-4 pt-2">
            <li>Delete the Scan Report</li>
            <li>Delete the Scan Report file and data dictionary</li>
            <li>
              Delete the mapping rules and will not enable them to be reused
            </li>
            <li>
              If any mapping rules have already been reused in other Scan
              Reports, they will not be deleted
            </li>
          </ul>
        </DialogHeader>
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

export default DeleteDialog;

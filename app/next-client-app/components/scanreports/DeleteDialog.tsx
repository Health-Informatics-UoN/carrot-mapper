"use client";
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
import { DialogTrigger } from "@radix-ui/react-dialog";
import { useRouter } from "next/navigation";
import { Loader2, TrashIcon } from "lucide-react";
import { DropdownMenuItem } from "../ui/dropdown-menu";
import { useEffect, useState } from "react";

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
  isOpen,
  setOpen = () => { },
  needTrigger = false
}: DeleteDialogProps) => {
  const router = useRouter();
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (!isDeleting) return;
    const warnBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [isDeleting]);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      const response = await deleteScanReport(id);
      if (response) {
        toast.error(
          `Failed to delete the Scan Report: ${response.errorMessage}`
        );
      } else {
        toast.success("Scan Report successfully deleted");
      }
    } finally {
      setIsDeleting(false);
    }
    setOpen(false);
    if (redirect) router.push("/scanreports/");
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={() => {
        if (!isDeleting) setOpen(false);
      }}
    >
      {needTrigger && (
        <DialogTrigger asChild>
          <DropdownMenuItem
            variant="destructive"
            onSelect={(e) => e.preventDefault()}
          >
            <TrashIcon />
            Delete
          </DropdownMenuItem>
        </DialogTrigger>
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
          {isDeleting && (
            <p className="text-sm font-medium pt-2" role="status">
              Deleting the Scan Report. This can take a few minutes for large
              reports, please don&apos;t refresh or leave the page.
            </p>
          )}
        </DialogHeader>
        <DialogFooter className="flex-col space-y-2 sm:space-y-0 sm:space-x-2">
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={isDeleting}
          >
            {isDeleting && <Loader2 className="h-4 w-4 animate-spin" />}
            {isDeleting ? "Deleting..." : "Delete"}
          </Button>
          <DialogClose asChild>
            <Button variant="outline" disabled={isDeleting}>
              Cancel
            </Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default DeleteDialog;

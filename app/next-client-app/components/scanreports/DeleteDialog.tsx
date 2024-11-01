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
import { deleteScanReport } from "@/api/scanreports";
import { DialogTrigger } from "@radix-ui/react-dialog";
import { useRouter } from "next/navigation";
import { TrashIcon } from "lucide-react";

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
  setOpen = () => {},
  needTrigger = false,
}: DeleteDialogProps) => {
  const router = useRouter();

  const handleDelete = async () => {
    const response = await deleteScanReport(id);
    if (response) {
      toast.error(`Failed to delete the Scan Report: ${response.errorMessage}`);
    } else {
      toast.success("Scan Report successfully deleted");
    }
    setOpen(false);
    if (redirect) router.push("/scanreports/");
  };

  return (
    <Dialog open={isOpen} onOpenChange={() => setOpen(false)}>
      {/* TODO: Make the dropdown close when the trigger is clicked */}
      {needTrigger && (
        <DialogTrigger asChild>
          <div className="hover:bg-carrot-200 text-red-400 relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors focus:bg-carrot-100 focus:text-carrot-900 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 dark:focus:bg-carrot-800 dark:focus:text-carrot-50">
            <TrashIcon className="mr-2 size-4" />
            Delete Scan Report
          </div>
        </DialogTrigger>
      )}
      <DialogContent>
        <DialogHeader className="text-start">
          <DialogTitle>Delete Scan Report</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete this Scan Report? This will:
          </DialogDescription>
          <ul className="text-gray-500 list-disc pl-4 pt-2">
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
            <Button className="bg-black text-white">Cancel</Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default DeleteDialog;

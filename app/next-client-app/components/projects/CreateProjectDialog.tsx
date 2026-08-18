"use client";

import { DialogDescription } from "@radix-ui/react-dialog";
import { Plus } from "lucide-react";
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "../ui/button";
import { CreateProjectForm } from "./CreateProjectForm";

export function CreateProjectDialog({ users }: { users: User[] }) {
  const [dialogOpened, setDialogOpened] = useState(false);

  return (
    <Dialog open={dialogOpened} onOpenChange={setDialogOpened}>
      <DialogTrigger asChild>
        <Button variant={"outline"} className="ml-4 flex">
          New Project <Plus />
        </Button>
      </DialogTrigger>
      <DialogContent className="w-full bg-background text-foreground">
        <DialogHeader>
          <DialogTitle className="text-center">
            Create a New Project
          </DialogTitle>
        </DialogHeader>
        <DialogDescription className="justify-center items-center text-center">
          You will automatically be added as an admin of the new Project.
        </DialogDescription>
        <CreateProjectForm users={users} setDialogOpened={setDialogOpened} />
      </DialogContent>
    </Dialog>
  );
}

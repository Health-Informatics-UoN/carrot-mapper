"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { DialogTrigger } from "@radix-ui/react-dialog";
import { DataTable } from "../data-table";
import { columns } from "./columns";
import { GeneralStatus } from "@/constants/job";
import { StatusIcon } from "../core/StatusIcon";

interface JobProps {
  jobGroups: Job[][];
  generalStatus: string;
  table_name: string;
}

export default function JobDialog({
  jobGroups,
  table_name,
  generalStatus,
}: JobProps) {
  return (
    <Dialog>
      <DialogTrigger disabled={generalStatus == "NOT_STARTED"}>
        <div role="button">
          <StatusIcon
            status={{ value: generalStatus }}
            statusOptions={GeneralStatus}
          />
        </div>
      </DialogTrigger>
      <DialogContent className="max-w-screen-xl overflow-auto h-1/2">
        <DialogHeader>
          <DialogTitle className="flex justify-center text-center">
            Table: {table_name} - Job Progress Details
          </DialogTitle>
        </DialogHeader>
        {jobGroups.length > 0
          ? jobGroups.map((jobs, index) => (
              <DataTable
                key={index}
                columns={columns}
                data={jobs}
                count={jobs.length}
                paginated={false}
                viewColumns={false}
                overflow={false}
              />
            ))
          : "Retrieving Jobs"}
      </DialogContent>
    </Dialog>
  );
}

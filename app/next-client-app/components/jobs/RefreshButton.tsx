"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { getJobs } from "@/api/scanreports";
import { toast } from "sonner";

interface RefreshButtonProps {
  scanReportId: string;
  onJobsRefresh: (updatedJobs: Job[]) => void;
}

export function RefreshButton({
  scanReportId,
  onJobsRefresh,
}: RefreshButtonProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    try {
      setIsRefreshing(true);
      // Fetch jobs data
      const updatedJobs = await getJobs(scanReportId);
      if (updatedJobs) {
        onJobsRefresh(updatedJobs);
      }
    } catch (error: any) {
      toast.error("Failed to refresh jobs:", error);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <Button
      variant="outline"
      onClick={handleRefresh}
      disabled={isRefreshing}
      className="ml-2"
    >
      {isRefreshing ? (
        <>Refreshing...</>
      ) : (
        <>
          <RefreshCw />
          Refresh Jobs Progress
        </>
      )}
    </Button>
  );
}

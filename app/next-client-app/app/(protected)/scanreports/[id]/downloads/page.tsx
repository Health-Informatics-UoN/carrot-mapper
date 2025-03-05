import { FilterParameters } from "@/types/filter";
import { objToQuery } from "@/lib/client-utils";
import { DataTable } from "@/components/data-table";
import { list } from "@/api/files";
import { columns } from "./columns";
import { getJobs } from "@/api/scanreports";
import { DownloadStatus } from "./download-status";

interface DownloadsProps {
  params: {
    id: string;
  };
  searchParams?: FilterParameters;
}

export default async function Downloads({
  params: { id },
  searchParams,
}: DownloadsProps) {
  const defaultPageSize = 20;
  const defaultParams = {
    p: 1,
    page_size: defaultPageSize,
  };
  const combinedParams = { ...defaultParams, ...searchParams };
  const query = objToQuery(combinedParams);
  const downloadingJob = await getJobs(id, "download");
  const filesList = await list(Number(id), query);

  let lastestJob: Job | null = null;

  if (downloadingJob) {
    lastestJob = downloadingJob[0];
  }

  return (
    <div>
      {filesList && (
        <DataTable
          columns={columns}
          data={filesList.results}
          count={filesList.count}
          Filter={
            lastestJob?.status.value == "IN_PROGRESS" ||
            lastestJob?.status.value == "FAILED" ? (
              <DownloadStatus lastestJob={lastestJob} />
            ) : undefined
          }
          defaultPageSize={defaultPageSize}
        />
      )}
    </div>
  );
}

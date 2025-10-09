import { objToQuery } from "@/lib/client-utils";
import { list } from "@/api/files";
import { columns } from "./columns";
import { getJobs } from "@/api/scanreports";
import { DownloadStatus } from "./download-status";
import { FileDownloadsTable } from "./FileDownloadsTable";

interface DownloadsProps {
  params: Promise<{
    id: string;
  }>;
  searchParams?: Promise<FilterParameters>;
}

export default async function Downloads(props: DownloadsProps) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const { id } = params;

  const defaultPageSize = 20;
  const defaultParams = {
    p: 1,
    page_size: defaultPageSize
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
        <FileDownloadsTable
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

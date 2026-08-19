import { objToQuery } from "@/lib/client-utils";
import { DataTable } from "@/components/data-table";
import { getScanReportActivityLogs } from "@/api/activityLog";
import { columns } from "@/components/activity-log/columns";

interface LogsProps {
  params: Promise<{
    id: string;
  }>;
  searchParams?: Promise<FilterParameters>;
}

export default async function Logs(props: LogsProps) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const { id } = params;

  const defaultPageSize = 20;
  const defaultParams = {
    p: 1,
    page_size: defaultPageSize,
  };
  const combinedParams = { ...defaultParams, ...searchParams };
  const query = objToQuery(combinedParams);
  const logs = await getScanReportActivityLogs(id, query);

  return (
    <div>
      {logs && (
        <DataTable
          columns={columns}
          data={logs.results}
          count={logs.count}
          defaultPageSize={defaultPageSize}
        />
      )}
    </div>
  );
}

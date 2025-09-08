import { columns } from "@/app/(protected)/scanreports/[id]/mapping_rules/columns";
import { getSummaryRules } from "@/api/mapping-rules";
import { DataTable } from "@/components/data-table";
import { objToQuery } from "@/lib/client-utils";
import { RulesButton } from "../mapping_rules/rules-buttons";
import { getScanReport } from "@/api/scanreports";

interface SummaryProps {
  params: Promise<{
    id: string;
  }>;
  searchParams?: Promise<FilterParameters>;
}

export default async function SummaryViewDialog(props: SummaryProps) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const {
    id
  } = params;

  const defaultPageSize = 20;
  const defaultParams = {
    p: 1,
    page_size: defaultPageSize,
  };
  const combinedParams = { ...defaultParams, ...searchParams };
  const query = objToQuery(combinedParams);

  const summaryRules = await getSummaryRules(id, query);
  const scanReport = await getScanReport(id);
  const fileName = `${
    scanReport?.dataset
  } Rules - ${new Date().toLocaleString()}`;
  const rulesButton = (
    <RulesButton scanreportId={id} query={query} filename={fileName} />
  );
  // TODO: Make the loading state, if possible
  return (
    <DataTable
      columns={columns}
      data={summaryRules.results}
      count={summaryRules.count}
      defaultPageSize={defaultPageSize}
      Filter={rulesButton}
    />
  );
}

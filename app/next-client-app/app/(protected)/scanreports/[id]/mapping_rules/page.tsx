import { getMappingRulesList } from "@/api/mapping-rules";
import { objToQuery } from "@/lib/client-utils";
import { DataTable } from "@/components/data-table";
import { columns } from "./columns";
import { RulesButton } from "./rules-buttons";
import { getScanReport } from "@/api/scanreports";

interface ScanReportsMappingRulesProps {
  params: Promise<{
    id: string;
  }>;
  searchParams?: Promise<FilterParameters>;
}

export default async function ScanReportsMappingRules(props: ScanReportsMappingRulesProps) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const {
    id
  } = params;

  const defaultPageSize = 30;
  const defaultParams = {
    p: 1,
    page_size: defaultPageSize,
  };
  const combinedParams = { ...defaultParams, ...searchParams };
  const query = objToQuery(combinedParams);
  const mappingRulesList = await getMappingRulesList(id, query);
  const scanReport = await getScanReport(id);
  const fileName = `${
    scanReport?.dataset
  } Rules - ${new Date().toLocaleString()}`;
  const rulesButton = (
    <RulesButton scanreportId={id} query={query} filename={fileName} />
  );

  return (
    <div>
      <DataTable
        columns={columns}
        data={mappingRulesList.results}
        count={mappingRulesList.count}
        defaultPageSize={defaultPageSize}
        Filter={rulesButton}
      />
    </div>
  );
}

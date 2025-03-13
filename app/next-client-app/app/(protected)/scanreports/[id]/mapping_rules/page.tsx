import { FilterParameters } from "@/types/filter";
import { getMappingRulesList } from "@/api/mapping-rules";
import { objToQuery } from "@/lib/client-utils";
import { DataTable } from "@/components/data-table";
import { columns } from "./columns";
import { RulesButton } from "./rules-buttons";
import { getScanReport } from "@/api/scanreports";

interface ScanReportsMappingRulesProps {
  params: {
    id: string;
  };
  searchParams?: FilterParameters;
}

export default async function ScanReportsMappingRules({
  params: { id },
  searchParams,
}: ScanReportsMappingRulesProps) {
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

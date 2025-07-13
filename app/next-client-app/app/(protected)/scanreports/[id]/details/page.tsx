import {
  getDataUsers,
  getDatasetList,
  getDatasetPermissions,
} from "@/api/datasets";
import { ScanReportDetailsForm } from "@/components/scanreports/ScanReportDetailsForm";
import { getScanReport, getScanReportPermissions } from "@/api/scanreports";
import { Forbidden } from "@/components/core/Forbidden";
import { notFound } from "next/navigation";

interface ScanReportDetailsProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function ScanreportDetails(props: ScanReportDetailsProps) {
  const params = await props.params;

  const {
    id
  } = params;

  const scanreport = await getScanReport(id);
  const datasetList = await getDatasetList();
  const users = await getDataUsers();
  const parent_dataset = datasetList.find(
    (dataset) => dataset.name === scanreport?.parent_dataset.name,
  );
  const permissionsDS = await getDatasetPermissions(
    parent_dataset?.id.toString() || "",
  );
  const permissionsSR = await getScanReportPermissions(id);
  const isAuthor = permissionsSR.permissions.includes("IsAuthor");

  if (!scanreport) {
    return notFound();
  }

  if (permissionsDS.permissions.length === 0) {
    return (
      <div>
        <Forbidden />
      </div>
    );
  }

  return (
    <ScanReportDetailsForm
      scanreport={scanreport}
      datasetList={datasetList}
      users={users}
      permissions={permissionsDS.permissions}
      isAuthor={isAuthor}
    />
  );
}

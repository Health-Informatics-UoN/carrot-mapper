import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  getDataUsers,
  getDatasetList,
  getDatasetPermissions,
} from "@/api/datasets";
import { ScanReportDetailsForm } from "@/components/scanreports/ScanReportDetailsForm";
import { getScanReport, getScanReportPermissions } from "@/api/scanreports";

interface ScanReportDetailsProps {
  params: {
    id: string;
  };
}

export default async function ScanreportDetails({
  params: { id },
}: ScanReportDetailsProps) {
  const scanreport = await getScanReport(id);
  const datasetList = await getDatasetList();
  const users = await getDataUsers();
  const parent_dataset = datasetList.find(
    (dataset) => dataset.name === scanreport.parent_dataset
  );
  const permissionsDS = await getDatasetPermissions(
    parent_dataset?.id.toString() || ""
  );
  const permissionsSR = await getScanReportPermissions(id);
  const isAuthor = permissionsSR.permissions.includes("IsAuthor");

  return (
    <div className="pt-10 px-16">
      <div>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="/">Home</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>/</BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbLink href="/scanreports">Scan Reports</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>/</BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbLink href={`/scanreports/${id}/`}>
                {scanreport.dataset}
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>/</BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbLink href={`/scanreports/${id}/details`}>
                Details
              </BreadcrumbLink>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>
      <div className="flex justify-between mt-3">
        <h1 className="text-4xl font-semibold">
          Details Page - Scan Report #{id}
        </h1>
      </div>
      <div className="mt-4">
        <ScanReportDetailsForm
          scanreport={scanreport}
          datasetList={datasetList}
          users={users}
          permissions={permissionsDS.permissions}
          isAuthor={isAuthor}
        />
      </div>
    </div>
  );
}
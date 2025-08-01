import {
  getScanReport,
  getScanReportPermissions,
} from "@/api/scanreports";
import { Forbidden } from "@/components/core/Forbidden";
import { NavGroup } from "@/components/core/nav-group";
import DeleteDialog from "@/components/scanreports/DeleteDialog";
import { Button } from "@/components/ui/button";
import { FileScan, Folders, GripVertical } from "lucide-react";
import { Boundary } from "@/components/core/boundary";
import { AvatarList } from "@/components/core/avatar-list";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel
} from "@/components/ui/dropdown-menu";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns/format";
import { InfoItem } from "@/components/core/InfoItem";
import { notFound } from "next/navigation";
import Link from "next/link";
import { MappingStatus } from "@/components/scanreports/MappingStatus";
import { StatusIcon } from "@/components/core/StatusIcon";
import { UploadStatusOptions } from "@/constants/scanReportStatus";
import ExportScanReport from "@/components/scanreports/ExportScanReport";
import { ActionsDownloadMenu } from "./actions-download-menu";

export default async function ScanReportLayout(
  props: Readonly<{
    params: { id: string };
    children: React.ReactNode;
  }>
) {
  const params = await props.params;

  const { children } = props;

  const permissions = await getScanReportPermissions(params.id);
  const requiredPermissions: Permission[] = ["CanAdmin", "CanEdit", "CanView"];
  const canEdit =
    permissions.permissions.includes("CanEdit") ||
    permissions.permissions.includes("CanAdmin");

  const items = [
    {
      name: "Tables",
      iconName: "TableProperties",
      matchPrefixes: ["tables"]
    },
    { name: "Rules", slug: "mapping_rules", iconName: "Waypoints" },
    { name: "Review Rules", slug: "review_rules", iconName: "SearchCheck" },
    { name: "Downloads", slug: "downloads", iconName: "Download" }
  ];

  {
    /* Pushed the Edit button to the Items above so it appears on same level */
  }
  if (canEdit) {
    items.push({
      name: "Edit Details",
      slug: "details",
      iconName: "Edit"
    });
  }

  const scanreport = await getScanReport(params.id);

  if (!scanreport) {
    return notFound();
  }

  if (
    !requiredPermissions.some((permission) =>
      permissions.permissions.includes(permission)
    )
  ) {
    return <Forbidden />;
  }

  const createdDate = new Date(scanreport.created_at);
  return (
    <div className="space-y-2">
      {/* Details line */}
      <div className="flex font-semibold text-xl items-center space-x-2">
        <Link href={`/datasets/${scanreport.parent_dataset.id}`}>
          <h2 className="flex items-center text-muted-foreground">
            <Folders className="mr-2" />
            {scanreport.parent_dataset.name}
          </h2>
        </Link>
        <h2 className="text-muted-foreground">{"/"}</h2>
        <Link href={`/scanreports/${scanreport.id}`}>
          <h2 className="flex items-center">
            <FileScan className="mr-2 text-green-700" />
            {scanreport.dataset}
          </h2>
        </Link>
      </div>

      <div className="flex flex-col md:flex-row md:items-center h-7 text-sm space-y-2 md:space-y-0 divide-y md:divide-y-0 md:divide-x">
        <InfoItem
          label="Data Partner"
          value={scanreport.data_partner}
          className="py-1 md:py-0 md:pr-3"
        />
        <InfoItem
          label="Author"
          value={scanreport.author.username}
          className="py-1 md:py-0 md:px-3"
        />
        <InfoItem
          label="Created"
          value={format(createdDate, "MMM dd, yyyy h:mm a")}
          className="py-1 md:py-0 md:px-3"
        />
        <div className="py-1 md:py-0 md:px-3 h-5 flex items-center gap-2 text-muted-foreground">
          Upload status:{" "}
          <StatusIcon
            statusOptions={UploadStatusOptions}
            status={scanreport.upload_status || { value: "IN_PROGRESS" }}
            statusDetails={scanreport.upload_status_details}
          />
        </div>
        <div className="py-1 md:py-0 md:px-3 h-5">
          <MappingStatus
            id={params.id}
            mapping_status={scanreport.mapping_status || { value: "PENDING" }}
            dataset={scanreport.dataset}
            className="w-[180px] h-5"
            disabled={
              !canEdit || scanreport.upload_status?.value !== "COMPLETE"
            }
          />
        </div>
        
        
      </div>
      <div className="flex flex-col md:flex-row md:items-center h-7 text-sm space-y-2 md:space-y-0 divide-y md:divide-y-0 md:divide-x">
        <div className="flex items-center gap-2 text-muted-foreground">
            Members:{" "}
            <AvatarList
              members={[...scanreport.viewers, ...scanreport.editors].filter(
                (member, index, self) =>
                  index === self.findIndex((m) => m.id === member.id)
              )}
            />
          </div>
        </div>
      {/* "Navs" group */}
      <div className="flex flex-col md:flex-row justify-between">
        <div>
          <NavGroup
            path={`/scanreports/${params.id}`}
            items={items.map(x => ({ ...x, text: x.name }))}
          />
        </div>

        {/* Actions button */}
        <div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                Actions <GripVertical className="ml-2 size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <ActionsDownloadMenu scanreportId={params.id} />
              <DropdownMenuSeparator />
              <DropdownMenuLabel>Scan Report</DropdownMenuLabel>
              <ExportScanReport
                scanReportId={params.id}
                scanReportName={scanreport.dataset}
              />

              <DeleteDialog id={Number(params.id)} redirect needTrigger />
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
      <Boundary>
        <Suspense fallback={<Skeleton className="h-full w-full" />}>
          {children}
        </Suspense>
      </Boundary>
    </div>
  );
}

import { getScanReport, getScanReportPermissions } from "@/api/scanreports";
import { Forbidden } from "@/components/core/Forbidden";
import { NavGroup } from "@/components/core/nav-group";
import DeleteDialog from "@/components/scanreports/DeleteDialog";
import { Button } from "@/components/ui/button";
import {
  Download,
  Edit,
  FileScan,
  Folders,
  GripVertical,
  TrashIcon,
} from "lucide-react";
import { Boundary } from "@/components/core/boundary";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns/format";
import { UploadStatus } from "@/components/scanreports/UploadStatus";
import { InfoItem } from "@/components/core/InfoItem";
import { notFound } from "next/navigation";
import Link from "next/link";
import { MappingStatus } from "@/components/scanreports/MappingStatus";

export default async function ScanReportLayout({
  params,
  children,
}: Readonly<{
  params: { id: string };
  children: React.ReactNode;
}>) {
  const permissions = await getScanReportPermissions(params.id);
  const requiredPermissions: Permission[] = ["CanAdmin", "CanEdit", "CanView"];
  const canEdit =
    permissions.permissions.includes("CanEdit") ||
    permissions.permissions.includes("CanAdmin");

  const items = [
    {
      name: "Tables",
      iconName: "TableProperties",
    },
    { name: "Rules", slug: "mapping_rules", iconName: "Waypoints" },
    { name: "Review Rules", slug: "review_rules", iconName: "SearchCheck" },
    { name: "Downloads", slug: "downloads", iconName: "Download" },
  ];

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
          <h2 className="text-gray-500 dark:text-gray-400 flex items-center">
            <Folders className="text-gray-500 mr-2" />
            {scanreport.parent_dataset.name}
          </h2>
        </Link>
        <h2 className="text-gray-500 dark:text-gray-400">{"/"}</h2>
        <Link href={`/scanreports/${scanreport.id}`}>
          <h2 className="flex items-center">
            <FileScan className="text-green-700 mr-2" />
            {scanreport.dataset}
          </h2>
        </Link>
      </div>

      <div className="flex flex-col md:flex-row md:items-center h-7 text-sm space-y-2 md:space-y-0 divide-y md:divide-y-0 md:divide-x divide-gray-300">
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
        <div className="py-1 md:py-0 md:px-3 h-5 flex items-center gap-2">
          Upload status:{" "}
          <UploadStatus
            upload_status={scanreport.upload_status || { value: "IN_PROGRESS" }}
          />
        </div>
        <div className="py-1 md:py-0 md:px-3 h-5">
          <MappingStatus
            id={params.id}
            mapping_status={scanreport.mapping_status || { value: "PENDING" }}
            dataset={scanreport.dataset}
            className="w-[180px] h-5"
            disabled={!canEdit || scanreport.upload_status.value !== "COMPLETE"} // Disable when users don't have permission or upload status is not complete
          />
        </div>
      </div>
      {/* "Navs" group */}
      <div className="flex flex-col md:flex-row justify-between">
        <div>
          <NavGroup
            path={`/scanreports/${params.id}`}
            items={[
              ...items.map((x) => ({
                text: x.name,
                slug: x.slug,
                iconName: x.iconName,
              })),
            ]}
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
              <DropdownMenuItem>
                <a href={`/scanreports/${params.id}/details`} className="flex">
                  <Edit className="mr-2 size-4" />
                  Edit Scan Report Details
                </a>
              </DropdownMenuItem>
              <DropdownMenuItem>
                <a
                  href={`/api/v2/scanreports/${params.id}/download/`}
                  download
                  className="flex"
                >
                  <Download className="mr-2 size-4" />
                  Export Scan Report
                </a>
              </DropdownMenuItem>
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

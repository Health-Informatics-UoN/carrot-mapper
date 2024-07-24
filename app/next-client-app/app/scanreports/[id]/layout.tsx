import { getScanReport, getScanReportPermissions } from "@/api/scanreports";
import { Forbidden } from "@/components/core/Forbidden";
import { TabGroup } from "@/components/ui/layout/tab-group";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import DeleteDialog from "@/components/scanreports/DeleteDialog";
import { Button } from "@/components/ui/button";
import {
  ChevronDown,
  Download,
  Edit,
  FileScan,
  GripVertical,
  TrashIcon,
} from "lucide-react";
import { Boundary } from "@/components/ui/layout/boundary";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns/format";

export default async function ScanReportLayout({
  params,
  children,
}: Readonly<{
  params: { id: string };
  children: React.ReactNode;
}>) {
  const permissions = await getScanReportPermissions(params.id);
  const requiredPermissions: Permission[] = ["CanAdmin", "CanEdit", "CanView"];

  const categories = [
    { name: "Rules", slug: "mapping_rules" },
    { name: "Review Rules", slug: "mapping_rules/summary" },
  ];

  const scanreport = await getScanReport(params.id);
  const createdDate = new Date(scanreport.created_at);
  if (
    !requiredPermissions.some((permission) =>
      permissions.permissions.includes(permission)
    )
  ) {
    return (
      <div className="pt-10 px-16">
        <Forbidden />
      </div>
    );
  }
  return (
    <>
      <div className="pt-10 px-16 space-y-3">
        <div>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink href="/">Home</BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator>/</BreadcrumbSeparator>
              <BreadcrumbItem>
                <BreadcrumbLink href="/scanreports">
                  Scan Reports
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator>/</BreadcrumbSeparator>
              <BreadcrumbItem>
                <BreadcrumbLink href={`/scanreports/${params.id}/`}>
                  {scanreport.dataset}
                </BreadcrumbLink>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </div>
        <div className="flex font-semibold text-3xl items-center">
          <FileScan className="mr-2 text-green-700" />
          <h2>{scanreport.dataset}</h2>
        </div>
        <div className="flex items-center text-md space-x-2">
          <div className="flex items-center space-x-2">
            <h3 className="text-gray-500">
              Status: <span className="text-black">{scanreport.status}</span>
            </h3>
          </div>
          <div className="flex items-center space-x-2">
            <h3 className="text-gray-500">
              | Dataset:
              <span className="text-black">{scanreport.parent_dataset}</span>
            </h3>
          </div>
          <div className="flex items-center space-x-2">
            <h3 className="text-gray-500">
              | Data Partner:{" "}
              <span className="text-black">{scanreport.data_partner}</span>
            </h3>
          </div>
          <div className="flex items-center space-x-2">
            <h3 className="text-gray-500">
              | Created Date:{" "}
              <span className="text-black">
                {format(createdDate, "MMM dd, yyyy h:mm a")}
              </span>
            </h3>
          </div>
        </div>

        <div className="flex justify-between">
          <TabGroup
            path={`/scanreports/${params.id}`}
            items={[
              {
                text: "Tables",
              },
              ...categories.map((x) => ({
                text: x.name,
                slug: x.slug,
              })),
            ]}
          />
          <div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  Actions <GripVertical className="ml-2 size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem>
                  <a
                    href={`/scanreports/${params.id}/details`}
                    className="flex"
                  >
                    <Edit className="mr-2 size-4" />
                    Edit Details
                  </a>
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <a
                    href={`/api/scanreports/${params.id}/download/`}
                    download
                    className="flex"
                  >
                    <Download className="mr-2 size-4" />
                    Export Scan Report
                  </a>
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <DeleteDialog id={Number(params.id)} redirect>
                    <Button
                      variant={"ghost"}
                      className="text-red-400 px-0 py-0 h-auto"
                    >
                      <TrashIcon className="mr-2 size-4" />
                      Delete Scan Report
                    </Button>
                  </DeleteDialog>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        <Boundary>
          {" "}
          <Suspense fallback={<Skeleton className="h-full w-full" />}>
            {children}
          </Suspense>
        </Boundary>
      </div>
    </>
  );
}

import { Forbidden } from "@/components/core/Forbidden";
import { NavGroup } from "@/components/core/nav-group";
import { Database } from "lucide-react";
import { Boundary } from "@/components/core/boundary";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns/format";
import { getDataSet, getDatasetPermissions } from "@/api/datasets";
import { Badge } from "@/components/ui/badge";
import { InfoItem } from "@/components/core/InfoItem";
import { AvatarList } from "@/components/core/avatar-list";
import Link from "next/link";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ChevronDownIcon, Folders } from "lucide-react";

interface LayoutProps {
  params: Promise<{ id: string }>;
  children: React.ReactNode;
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = await params;
  const dataset = await getDataSet(resolvedParams.id);
  return {
    title: `${dataset?.name} | Carrot Mapper`,
    description: `Dataset details for ${dataset?.name}`,
  };
}

export default async function DatasetLayout({
  params,
  children
}: Readonly<LayoutProps>) {
  const { id } = await params;

  const permissions = await getDatasetPermissions(id);
  const requiredPermissions: Permission[] = ["CanAdmin", "CanEdit", "CanView"];

  const items = [
    {
      name: "Scan Reports",
      iconName: "FileScan"
    },
    { name: "Edit Details", slug: "details", iconName: "Edit" }
  ];

  const dataset = await getDataSet(id);

  const dataPartner = dataset.data_partner;
  const projects = dataset.projects;

  const createdDate = new Date(dataset.created_at);
  if (
    !requiredPermissions.some((permission) =>
      permissions.permissions.includes(permission)
    )
  ) {
    return <Forbidden />;
  }
  return (
    <div className="space-y-2">
      <DatasetBreadcrumb projects={projects} datasetName={dataset.name} />

      <div className="flex flex-col md:flex-row md:items-center text-sm space-y-2 md:space-y-0 divide-y md:divide-y-0 md:divide-x divide-muted">
        <InfoItem
          label="Data Partner"
          value={dataPartner.name}
        />
        <InfoItem
          label="Created"
          value={format(createdDate, "MMM dd, yyyy h:mm a")}
          className="py-1 md:py-0 md:px-3"
        />
        
      </div>
      <div className="hidden md:flex flex-col md:flex-row md:items-center h-7 text-sm space-y-2 md:space-y-0 divide-y md:divide-y-0 md:divide-x">
        <div className="flex items-center gap-2 text-muted-foreground">
            Members:{" "}
            <AvatarList
              members={[...dataset.admins, ...dataset.viewers, ...dataset.editors].filter(
                (member, index, self) =>
                  index === self.findIndex((m) => m.id === member.id)
              )}
            />
        </div>
      </div>
      
      {/* "Navs" group */}
      <div className="flex justify-between">
        <NavGroup
          path={`/datasets/${id}`}
          items={[
            ...items.map((x) => ({
              text: x.name,
              slug: x.slug,
              iconName: x.iconName
            }))
          ]}
        />
      </div>
      <Boundary>
        {" "}
        <Suspense fallback={<Skeleton className="h-full w-full" />}>
          {children}
        </Suspense>
      </Boundary>
    </div>
  );
}

interface DatasetBreadcrumbProps {
  projects: Array<{ id: number; name: string }>;
  datasetName: string;
}

function DatasetBreadcrumb({ projects, datasetName }: DatasetBreadcrumbProps) {
  return (
    <div className="flex font-semibold text-xl items-center space-x-2">
      <Folders className="text-muted-foreground" />
      <Link href={`/projects/${projects[0].id}`}>
        <h2 className="text-muted-foreground">{projects[0].name}</h2>
      </Link>
      
      {projects.length > 1 && (
        <DropdownMenu>
          <DropdownMenuTrigger>
            <ChevronDownIcon size={16} />
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            {projects.map((project) => (
              <DropdownMenuItem key={project.id}>
                <Link href={`/projects/${project.id}`}>{project.name}</Link>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
      <h2 className="text-muted-foreground">{"/"}</h2>
      <Database className="mr-2 text-blue-700" />
      <h2>{datasetName}</h2>
    </div>
  );
}

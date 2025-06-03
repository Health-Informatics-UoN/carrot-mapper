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
import Link from "next/link";

interface LayoutProps {
  params: Promise<{ id: string }>;
  children: React.ReactNode;
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
      <div className="flex font-semibold text-xl items-center space-x-2">
        <Database className="text-muted-foreground" />
        <Link href={`/datasets`}>
          <h2 className="text-muted-foreground">Datasets</h2>
        </Link>
        <h2 className="text-muted-foreground">{"/"}</h2>
        <Database className="text-primary" />
        <h2>{dataset.name}</h2>
      </div>

      <div className="flex flex-col md:flex-row md:items-center text-sm space-y-2 md:space-y-0 divide-y md:divide-y-0 md:divide-x divide-muted">
        <h3 className="text-muted-foreground flex items-center gap-2 pr-2">
          <div>Project(s): </div>
          <div className="flex space-x-1">
            {projects.map((project) => (
              <Badge variant="outline" key={project.id}>
                {project.name}
              </Badge>
            ))}
          </div>
        </h3>
        <InfoItem
          label="Data Partner"
          value={dataPartner.name}
          className="py-1 md:py-0 md:px-3"
        />
        <InfoItem
          label="Created"
          value={format(createdDate, "MMM dd, yyyy h:mm a")}
          className="py-1 md:py-0 md:px-3"
        />
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

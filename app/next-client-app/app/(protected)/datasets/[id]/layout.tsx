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

export default async function DatasetLayout(
  props: Readonly<{
    params: { id: string };
    children: React.ReactNode;
  }>
) {
  const { params, children } = props;

  const permissions = await getDatasetPermissions(params.id);
  const requiredPermissions: Permission[] = ["CanAdmin", "CanEdit", "CanView"];

  const items = [
    {
      name: "Scan Reports",
      iconName: "FileScan",
    },
    { name: "Edit Details", slug: "details", iconName: "Edit" },
  ];

  const dataset = await getDataSet(params.id);
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
        <Database className="text-gray-500" />
        <Link href={`/datasets`}>
          <h2 className="text-gray-500 dark:text-gray-400">Datasets</h2>
        </Link>
        <h2 className="text-gray-500 dark:text-gray-400">{"/"}</h2>
        <Database className="text-blue-700" />
        <h2>{dataset.name}</h2>
      </div>

      <div className="flex flex-col md:flex-row md:items-center text-sm space-y-2 md:space-y-0 divide-y md:divide-y-0 md:divide-x divide-gray-300">
        <h3 className="text-gray-500 dark:text-gray-400 flex items-center gap-2 pr-2">
          <div>Project(s): </div>
          <div className="flex space-x-1">
            {projects.map((project) => (
              <Badge
                variant={"outline"}
                className="bg-carrot-100 dark:bg-carrot-700"
                key={project.id}
              >
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

      <div className="flex justify-between">
        <NavGroup
          path={`/datasets/${params.id}`}
          items={items.map((x) => ({
            text: x.name,
            slug: x.slug,
            iconName: x.iconName,
          }))}
        />
      </div>

      <Boundary>
        <Suspense fallback={<Skeleton className="h-full w-full" />}>
          {children}
        </Suspense>
      </Boundary>
    </div>
  );
}

import { Forbidden } from "@/components/core/Forbidden";
import { NavGroup } from "@/components/core/nav-group";
import { Folders } from "lucide-react";
import { Boundary } from "@/components/core/boundary";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns/format";
import { InfoItem } from "@/components/core/InfoItem";
import Link from "next/link";
import { getProject } from "@/api/projects";
import { AvatarList } from "@/components/core/avatar-list";
import { ReactNode } from "react";


interface LayoutProps {
  params: Promise<{ id: string }>;
  children: ReactNode;
}

const items = [
  {
    name: "Datasets",
    slug: "",
    iconName: "Database",
  },
];

export default async function DatasetLayout({ params, children }: LayoutProps) {
  const resolvedParams = await params; // Await the promise to extract the actual value
  const project = await getProject(resolvedParams.id);
  let createdDate = new Date();

  if (!project) {
    return <Forbidden />;
  }

  createdDate = new Date(project.created_at);

  return (
    <div className="space-y-2">
      <div className="flex font-semibold text-xl items-center space-x-2">
        <Folders />
        <Link href={`/projects`}>
          <h2>Projects</h2>
        </Link>
        <h2>{"/"}</h2>
        <Folders />
        <h2>{project?.name}</h2>
      </div>

      <div className="flex flex-col md:flex-row md:items-center text-sm space-y-2 md:space-y-0 divide-y md:divide-y-0 md:divide-x">
        <InfoItem
          label="Created"
          value={format(createdDate, "MMM dd, yyyy h:mm a")}
          className="py-1 md:py-0 md:pr-3"
        />
        <div className="py-1 md:py-0 md:px-3 h-5 flex items-center gap-2">
          Members: <AvatarList members={project?.members || []} />
        </div>
      </div>
      {/* "Navs" group */}
      <div className="flex justify-between">
        <NavGroup
          path={`/projects/${resolvedParams.id}`}
          items={[
            ...items.map((x) => ({
              text: x.name,
              slug: x.slug,
              iconName: x.iconName,
            })),
          ]}
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
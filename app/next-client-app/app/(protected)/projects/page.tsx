import { DataTable } from "@/components/data-table";
import { columns } from "./columns";
import { objToQuery } from "@/lib/client-utils";
import { DataTableFilter } from "@/components/data-table/DataTableFilter";
import { FilterParameters } from "@/types/filter";
import { Folders } from "lucide-react";
import { getProjectsList } from "@/api/projects";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Projects | Carrot Mapper",
  description: "Projects for the current user",
};

interface ProjectListProps {
  searchParams?: Promise<FilterParameters>;
}

export default async function Projects(props: ProjectListProps) {
  const searchParams = await props.searchParams;
  const defaultParams = {
    page_size: 10,
  };
  const combinedParams = { ...defaultParams, ...searchParams };
  const query = objToQuery(combinedParams);
  const projects = await getProjectsList(query);

  const filter = <DataTableFilter filter="name" />;

  return (
    <div className="space-y-2">
      <div className="flex font-semibold text-xl items-center">
        <Folders className="mr-2 text-orange-700" />
        <h2>Projects</h2>
      </div>
      <div>
        <DataTable
          columns={columns}
          data={projects.results}
          count={projects.count}
          Filter={filter}
        />
      </div>
    </div>
  );
}

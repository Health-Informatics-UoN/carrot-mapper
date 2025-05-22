import { DataTable } from "@/components/data-table";
import { objToQuery } from "@/lib/client-utils";
import { FilterParameters } from "@/types/filter";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataTableFilter } from "@/components/data-table/DataTableFilter";
import { getDataSets } from "@/api/datasets";
import { columns } from "../../datasets/columns";

interface ProjectDetailProps {
  params: Promise<{
    id: string;
  }>;
  searchParams?: Promise<{ status__in: string } & FilterParameters>;
}

export default async function ProjectDetail(props: ProjectDetailProps) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const {
    id
  } = params;

  const defaultParams = {
    hidden: false,
    page_size: 10,
    project: id,
  };
  const combinedParams = { ...defaultParams, ...searchParams };
  const query = objToQuery(combinedParams);
  const datasets = await getDataSets(query);
  const filter = <DataTableFilter filter="name" />;

  return (
    <Tabs
      defaultValue={
        (searchParams as any)?.hidden
          ? (searchParams as any)?.hidden === "true"
            ? "archived"
            : "active"
          : "active"
      }
    >
      <div className="flex justify-between items-center">
        <TabsList>
          <a href="?hidden=false" className="h-full">
            <TabsTrigger value="active">Active Datasets</TabsTrigger>
          </a>
          <a href="?hidden=true" className="h-full">
            <TabsTrigger value="archived">Archived Datasets</TabsTrigger>
          </a>
        </TabsList>
      </div>
      <TabsContent value="active">
        <DataTable
          columns={columns}
          data={datasets.results}
          count={datasets.count}
          Filter={filter}
        />
      </TabsContent>
      <TabsContent value="archived">
        <DataTable
          columns={columns}
          data={datasets.results}
          count={datasets.count}
          Filter={filter}
        />
      </TabsContent>
    </Tabs>
  );
}

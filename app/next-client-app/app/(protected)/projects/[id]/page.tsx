import { DataTable } from "@/components/data-table";
import { objToQuery } from "@/lib/client-utils";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataTableFilter } from "@/components/data-table/DataTableFilter";
import { getDataSets } from "@/api/datasets";
import { columns } from "../../datasets/columns";
import { EmptyState } from "@/components/ui/empty-state";

interface ProjectDetailProps {
  params: Promise<{
    id: string;
  }>;
  searchParams?: Promise<{ status__in: string } & FilterParameters>;
}

export default async function ProjectDetail(props: ProjectDetailProps) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const { id } = params;

  const defaultParams = {
    hidden: false,
    page_size: 10,
    project: id
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
        {datasets.results.length > 0 ? (
          <DataTable
            columns={columns}
            data={datasets.results}
            count={datasets.count}
            Filter={filter}
          />
        ) : (
          <EmptyState
            icon="database"
            title="No datasets in this project"
            description="Create your first dataset in this project to start organizing and mapping your data."
          />
        )}
      </TabsContent>
      <TabsContent value="archived">
        {datasets.results.length > 0 ? (
          <DataTable
            columns={columns}
            data={datasets.results}
            count={datasets.count}
            Filter={filter}
          />
        ) : (
          <EmptyState
            icon="database"
            title="No archived datasets"
            description="No archived datasets found in this project. Active datasets will appear here when archived."
          />
        )}
      </TabsContent>
    </Tabs>
  );
}

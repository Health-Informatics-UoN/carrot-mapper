import { DataTable } from "@/components/data-table";
import { columns } from "./columns";
import { getDataPartners, getDataSets } from "@/api/datasets";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { objToQuery } from "@/lib/client-utils";
import { DataTableFilter } from "@/components/data-table/DataTableFilter";
import { FilterParameters } from "@/types/filter";
import { CreateDatasetDialog } from "@/components/datasets/CreateDatasetDialog";
import { Database } from "lucide-react";
import { getAllProjects } from "@/api/projects";

interface DataSetListProps {
  searchParams?: Promise<FilterParameters>;
}

export default async function DataSets(props: DataSetListProps) {
  const searchParams = await props.searchParams;
  const defaultParams = {
    hidden: false,
    page_size: 10,
  };
  const combinedParams = { ...defaultParams, ...searchParams };

  const projects = await getAllProjects();
  const dataPartnerList = await getDataPartners();
  const query = objToQuery(combinedParams);
  const dataset = await getDataSets(query);
  const filter = <DataTableFilter filter="name" />;

  return (
    <div className="space-y-2">
      <div className="flex font-semibold text-xl items-center">
        <Database className="mr-2 text-primary" />
        <h2>Datasets</h2>
      </div>
      <div className="my-3 justify-between">
        <div>
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
              <TabsList className="mb-2">
                <a href="?hidden=false" className="h-full">
                  <TabsTrigger value="active">Active Datasets</TabsTrigger>
                </a>
                <a href="?hidden=true" className="h-full">
                  <TabsTrigger value="archived">Archived Datasets</TabsTrigger>
                </a>
              </TabsList>
              <div className="hidden md:flex">
                <CreateDatasetDialog
                  projects={projects}
                  dataPartnerList={dataPartnerList}
                />
              </div>
            </div>
            <TabsContent value="active">
              <DataTable
                columns={columns}
                data={dataset.results}
                count={dataset.count}
                Filter={filter}
              />
            </TabsContent>
            <TabsContent value="archived">
              <DataTable
                columns={columns}
                data={dataset.results}
                count={dataset.count}
                Filter={filter}
              />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}

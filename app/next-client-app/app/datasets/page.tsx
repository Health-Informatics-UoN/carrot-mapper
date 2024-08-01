import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { DataTable } from "@/components/data-table";
import { columns } from "./columns";
import { getDataPartners, getDataSets, getProjects } from "@/api/datasets";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { objToQuery } from "@/lib/client-utils";
import { DataTableFilter } from "@/components/data-table/DataTableFilter";
import { FilterParameters } from "@/types/filter";
import { CreateDatasetDialog } from "@/components/datasets/CreateDatasetDialog";

interface DataSetListProps {
  searchParams?: FilterParameters;
}

export default async function DataSets({ searchParams }: DataSetListProps) {
  // TODO: ADD default page size here
  const defaultParams = {
    hidden: false,
    page_size: 10,
  };
  const combinedParams = { ...defaultParams, ...searchParams };

  const projects = await getProjects();
  const dataPartnerList = await getDataPartners();
  const query = objToQuery(combinedParams);
  const dataset = await getDataSets(query);
  const filter = <DataTableFilter filter="name" />;

  return (
    <div className="pt-10 px-16">
      <div>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="/">Home</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>/</BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbLink href="/datasets">Datasets</BreadcrumbLink>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>
      <div className="flex justify-between mt-3">
        <h1 className="text-4xl font-semibold">Dataset List</h1>
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
              <div>
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

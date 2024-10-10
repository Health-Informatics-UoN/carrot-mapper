import {
  getDataPartners,
  getDataSet,
  getDataUsers,
  getDatasetPermissions,
} from "@/api/datasets";
import { getProjectsList } from "@/api/projects";
import { DatasetForm } from "@/components/datasets/DatasetForm";

interface DataSetListProps {
  params: {
    id: string;
  };
}

export default async function DatasetDetails({
  params: { id },
}: DataSetListProps) {
  const dataset = await getDataSet(id);
  const partners = await getDataPartners();
  const users = await getDataUsers();
  const projects = await getProjectsList();
  const permissions = await getDatasetPermissions(id);

  return (
    <DatasetForm
      dataset={dataset}
      dataPartners={partners}
      users={users}
      projects={projects.results}
      permissions={permissions.permissions}
    />
  );
}

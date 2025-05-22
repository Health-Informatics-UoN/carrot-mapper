import {
  getDataPartners,
  getDataSet,
  getDataUsers,
  getDatasetPermissions,
} from "@/api/datasets";
import { getAllProjects } from "@/api/projects";
import { DatasetForm } from "@/components/datasets/DatasetForm";

export default async function DatasetDetails({
  params,
}: {
  params: { id: string };
}) {
  const dataset = await getDataSet(params.id);
  const partners = await getDataPartners();
  const users = await getDataUsers();
  const projects = await getAllProjects();
  const permissions = await getDatasetPermissions(params.id);

  return (
    <DatasetForm
      dataset={dataset}
      dataPartners={partners}
      users={users}
      projects={projects}
      permissions={permissions.permissions}
    />
  );
}

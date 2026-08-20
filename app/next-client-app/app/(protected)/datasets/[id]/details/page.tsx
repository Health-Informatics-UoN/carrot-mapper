import {
  getDataPartners,
  getDataSet,
  getDataUsers,
  getDatasetPermissions,
} from "@/api/datasets";
import { getAllProjects } from "@/api/projects";
import { DatasetForm } from "@/components/datasets/DatasetForm";

interface DataSetListProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function DatasetDetails(props: DataSetListProps) {
  const params = await props.params;

  const { id } = params;

  const [dataset, partners, users, projects, permissions] = await Promise.all([
    getDataSet(id),
    getDataPartners(),
    getDataUsers(),
    getAllProjects(),
    getDatasetPermissions(id),
  ]);

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

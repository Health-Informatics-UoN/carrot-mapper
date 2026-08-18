import { getDataUsers } from "@/api/datasets";
import { getProject, getProjectPermissions } from "@/api/projects";
import { ProjectForm } from "@/components/projects/ProjectForm";
import { Forbidden } from "@/components/core/Forbidden";

interface ProjectDetailsProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function ProjectDetails(props: ProjectDetailsProps) {
  const { id } = await props.params;

  const project = await getProject(id);
  const users = await getDataUsers();
  const permissions = await getProjectPermissions(id);

  if (!project) {
    return <Forbidden />;
  }

  return (
    <ProjectForm
      project={project}
      users={users}
      permissions={permissions.permissions}
    />
  );
}

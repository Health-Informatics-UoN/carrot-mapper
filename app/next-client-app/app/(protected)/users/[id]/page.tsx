import { Folders } from "lucide-react";
import Link from "next/link";
import { getDataPartners } from "@/api/datasets";
import { getCurrentUser, getSharedProjects, getUserProfile } from "@/api/users";
import { Forbidden } from "@/components/core/Forbidden";
import { InfoItem } from "@/components/core/InfoItem";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ProfileForm } from "@/components/users/ProfileForm";

interface UserProfilePageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: UserProfilePageProps) {
  const { id } = await params;
  const user = await getUserProfile(id);
  return {
    title: `${user?.username ?? "User"} | Carrot Mapper`,
    description: `Profile for ${user?.username ?? "user"}`,
  };
}

export default async function UserProfilePage({
  params,
}: UserProfilePageProps) {
  const { id } = await params;
  const [user, currentUser] = await Promise.all([
    getUserProfile(id),
    getCurrentUser(),
  ]);

  if (!user) {
    return <Forbidden />;
  }

  const isOwnProfile = currentUser?.id === user.id;
  const initials = user.username.charAt(0).toUpperCase();

  const [sharedProjects, dataPartners] = await Promise.all([
    isOwnProfile ? Promise.resolve([]) : getSharedProjects(id),
    isOwnProfile ? getDataPartners() : Promise.resolve([]),
  ]);

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <Avatar className="h-12 w-12">
          <AvatarFallback className="text-lg">{initials}</AvatarFallback>
        </Avatar>
        <h2 className="text-xl font-semibold">{user.username}</h2>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <InfoItem
            label="Data Partner"
            value={user.profile.data_partner?.name ?? "Not set"}
          />
          <InfoItem label="ORCID iD" value={user.profile.orcid ?? "Not set"} />
        </CardContent>
      </Card>

      {isOwnProfile ? (
        <Card>
          <CardHeader>
            <CardTitle>Edit Profile</CardTitle>
          </CardHeader>
          <CardContent>
            <ProfileForm user={user} dataPartners={dataPartners} />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Shared Projects</CardTitle>
          </CardHeader>
          <CardContent>
            {sharedProjects.length === 0 ? (
              <EmptyState
                icon="folders"
                title="No shared projects"
                description={`You and ${user.username} are not members of any of the same projects.`}
              />
            ) : (
              <ul className="space-y-2">
                {sharedProjects.map((project) => (
                  <li key={project.id}>
                    <Link
                      href={`/projects/${project.id}/`}
                      className="flex items-center gap-2 text-primary hover:underline"
                    >
                      <Folders className="h-4 w-4" />
                      {project.name}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

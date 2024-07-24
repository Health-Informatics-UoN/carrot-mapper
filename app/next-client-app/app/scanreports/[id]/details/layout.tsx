import { getScanReportPermissions } from "@/api/scanreports";
import { Forbidden } from "@/components/core/Forbidden";
import { TabGroup } from "@/components/ui/layout/tab-group";

export default async function ScanReportDetailsLayout({
  params,
  children,
}: Readonly<{
  params: { id: string };
  children: React.ReactNode;
}>) {
  const permissions = await getScanReportPermissions(params.id);
  const requiredPermissions: Permission[] = ["CanAdmin", "CanEdit", "CanView"];
  if (
    !requiredPermissions.some((permission) =>
      permissions.permissions.includes(permission)
    )
  ) {
    return (
      <div className="pt-10 px-16">
        <Forbidden />
      </div>
    );
  }
  return (
    <>
      <div>{children}</div>
    </>
  );
}
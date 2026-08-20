import Link from "next/link";
import type { Session } from "next-auth";
import { SidebarButton } from "./sidebar-button";
import { sidebarItems } from "./menuItems";
import { Sidebar } from "./sidebar";
import { ModeToggle } from "./mode-toggle";
import { UserMenu } from "@/components/core/UserMenu";
import { NotificationsLink } from "@/components/core/NotificationsLink";
import { getUnreadAppNotificationCount } from "@/api/notifications";

export const MenuBar = async ({ user }: { user?: Session["user"] | null }) => {
  const unreadCount = user ? await getUnreadAppNotificationCount() : 0;

  return (
    <>
      <Sidebar userName={user?.username} unreadCount={unreadCount} />
      <div className="hidden lg:flex lg:items-center sticky top-0 z-50 backdrop-blur-sm border-b border-border justify-between p-4 mb-4">
        <Link href={"/"}>
          <div className="text-2xl flex items-center font-semibold">
            <img
              className="w-[120px] dark:hidden"
              src="/carrot-logo.svg"
              alt="carrot-logo"
            />
            <img
              className="w-[120px] dark:block hidden"
              src="/carrot-logo-dark.svg"
              alt="carrot-logo"
            />
          </div>
        </Link>

        <div className="flex items-center gap-3">
          <div className="flex items-center">
            {(!user ? sidebarItems.routes : sidebarItems.links).map(
              (link, idx) => (
                <Link key={idx} href={link.href}>
                  <SidebarButton icon={link.icon} className="w-full">
                    {link.label}
                  </SidebarButton>
                </Link>
              ),
            )}
          </div>
          <div className="flex items-center gap-2">
            <ModeToggle />
            {user && <NotificationsLink initialUnreadCount={unreadCount} />}
            <UserMenu id={user?.pk} username={user?.username} />
          </div>
        </div>
      </div>
    </>
  );
};

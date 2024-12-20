import Link from "next/link";
import { SidebarButton } from "./sidebar-button";
import { sidebarItems } from "./menuItems";
import { Sidebar } from "./sidebar";
import { ModeToggle } from "./mode-toggle";
import { UserMenu } from "@/components/core/UserMenu";

export const MenuBar = ({ user }: { user?: User | null }) => {
  return (
    <>
      <Sidebar userName={user?.username} />
      <div className="hidden lg:flex lg:items-center sticky top-0 z-50 backdrop-blur border-b-2 border-gray-300 justify-between p-4 mb-4">
        <Link href={"/"}>
          <div className="text-2xl flex items-center font-semibold">
            <img
              className="mx-3 w-[25px]"
              src="/carrot-logo.png"
              alt="carrot-logo"
            />
            Carrot
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
            <UserMenu username={user?.username} />
          </div>
          <div>
            <ModeToggle />
          </div>
        </div>
      </div>
    </>
  );
};

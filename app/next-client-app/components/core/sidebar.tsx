"use client";

import { Sheet, SheetContent, SheetHeader, SheetTrigger } from "../ui/sheet";
import { Button } from "../ui/button";
import { LogOut, Menu, MoreHorizontal, Settings } from "lucide-react";
import Link from "next/link";
import { SidebarButton } from "./sidebar-button";
import { usePathname } from "next/navigation";
import { Separator } from "../ui/separator";
import { Drawer, DrawerContent, DrawerTrigger } from "../ui/drawer";
import { useEffect, useState } from "react";
import { ModeToggle } from "./mode-toggle";
import { sidebarItems } from "./menuItems";

export function Sidebar({ userName }: { userName?: string }) {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  return (
    <div className="flex gap-3 p-4 items-center justify-between border-b-2 border-gray-300 mb-4 lg:hidden">
      <div className="flex items-center">
        <div className="flex items-center">
          {" "}
          <Sheet open={isOpen} onOpenChange={setIsOpen}>
            <SheetTrigger asChild>
              <Button
                variant="outline"
                size={"sm"}
                className="mr-4 flex items-center justify-center"
                aria-label="Menu Button"
              >
                <Menu size={25} />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="px-3 py-4 w-[350px]">
              <SheetHeader className="flex flex-row justify-between items-center rounded-lg w-full py-3">
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
              </SheetHeader>
              <div className="h-full">
                <div className="flex mt-7 flex-col w-full gap-1">
                  {(userName ? sidebarItems.links : sidebarItems.routes).map(
                    (link, idx) => (
                      <Link key={idx} href={link.href}>
                        <SidebarButton
                          variant={
                            pathname === link.href ? "secondary" : "ghost"
                          }
                          icon={link.icon}
                          className="w-full"
                        >
                          {link.label}
                        </SidebarButton>
                      </Link>
                    ),
                  )}
                </div>
                {userName && (
                  <div className="absolute w-full bottom-4 px-1 left-0">
                    <Separator className="absolute -top-3 left-0 w-full" />
                    <Drawer>
                      <DrawerTrigger asChild>
                        <Button
                          variant="outline"
                          className="w-full justify-start"
                        >
                          <div className="flex justify-between items-center w-full">
                            <div className="flex gap-2">
                              <span>{userName}</span>
                            </div>
                            <MoreHorizontal size={20} />
                          </div>
                        </Button>
                      </DrawerTrigger>
                      <DrawerContent className="mb-2 p-2 w-[350px]">
                        <div className="flex flex-col space-y-2 mt-2">
                          <a href="/accounts/password_change/">
                            <SidebarButton
                              size="sm"
                              icon={Settings}
                              className="w-full"
                            >
                              Change Password
                            </SidebarButton>
                          </a>
                          <a href={"/accounts/logout/"}>
                            <SidebarButton
                              size="sm"
                              icon={LogOut}
                              className="w-full"
                            >
                              Log Out
                            </SidebarButton>
                          </a>
                        </div>
                      </DrawerContent>
                    </Drawer>
                  </div>
                )}
              </div>
            </SheetContent>
          </Sheet>
        </div>
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
      </div>
      <div className="justify-end">
        <ModeToggle />
      </div>
    </div>
  );
}

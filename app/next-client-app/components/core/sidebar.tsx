"use client";

import { Sheet, SheetContent, SheetHeader, SheetTrigger } from "../ui/sheet";
import { Button } from "../ui/button";
import {
  BookMarked,
  FileScan,
  Folders,
  Home,
  LogOut,
  LucideIcon,
  Menu,
  MoreHorizontal,
  Settings,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { SidebarButtonSheet as SidebarButton } from "./sidebar-button";
import { usePathname } from "next/navigation";
import { Separator } from "../ui/separator";
import { Drawer, DrawerContent, DrawerTrigger } from "../ui/drawer";
import Image from "next/image";

interface SidebarItems {
  links: Array<{
    label: string;
    href: string;
    icon?: LucideIcon;
  }>;
}

export function Sidebar() {
  const pathname = usePathname();

  const sidebarItems: SidebarItems = {
    links: [
      { label: "Home", href: "/", icon: Home },
      { label: "Datasets", href: "/datasets/", icon: Folders },
      { label: "Scan Reports", href: "/scanreports/", icon: FileScan },
      {
        label: "Upload Scan Report",
        href: "/scanreports/create/",
        icon: Upload,
      },
      {
        href: "https://carrot4omop.ac.uk",
        icon: BookMarked,
        label: "Documentation",
      },
    ],
  };

  return (
    <div className="flex gap-3 mt-3 px-10 items-center border-b-2 border-gray-300 pb-3">
      <div className="flex items-center">
        {" "}
        <Sheet>
          <SheetTrigger asChild>
            <Button size="icon" variant="ghost">
              <Menu size={25} />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="px-3 py-4">
            <SheetHeader className="flex flex-row justify-between items-center space-y-0">
              <span className="text-lg font-semibold text-foreground mx-3">
                Twitter
              </span>
            </SheetHeader>
            <div className="h-full">
              <div className="mt-5 flex flex-col w-full gap-1">
                {sidebarItems.links.map((link, idx) => (
                  <Link key={idx} href={link.href}>
                    <SidebarButton
                      variant={pathname === link.href ? "secondary" : "ghost"}
                      icon={link.icon}
                      className="w-full"
                    >
                      {link.label}
                    </SidebarButton>
                  </Link>
                ))}
              </div>
              <div className="absolute w-full bottom-4 px-1 left-0">
                <Separator className="absolute -top-3 left-0 w-full" />
                <Drawer>
                  <DrawerTrigger asChild>
                    <Button variant="outline" className="w-full justify-start">
                      <div className="flex justify-between items-center w-full">
                        <div className="flex gap-2">
                          {/* <Avatar className="h-5 w-5">
                        <AvatarImage src="https://github.com/max-programming.png" />
                        <AvatarFallback>Max Programming</AvatarFallback>
                      </Avatar>
                      <span>Max Programming</span> */}
                        </div>
                        <MoreHorizontal size={20} />
                      </div>
                    </Button>
                  </DrawerTrigger>
                  <DrawerContent className="mb-2 p-2">
                    <div className="flex flex-col space-y-2 mt-2">
                      <Link href="/">
                        <SidebarButton
                          size="sm"
                          icon={Settings}
                          className="w-full"
                        >
                          Account Settings
                        </SidebarButton>
                      </Link>
                      <SidebarButton size="sm" icon={LogOut} className="w-full">
                        Log Out
                      </SidebarButton>
                    </div>
                  </DrawerContent>
                </Drawer>
              </div>
            </div>
          </SheetContent>
        </Sheet>
      </div>
      {/* TODO: Need to confirm again this link */}
      <Link href={"/"}>
        <div className="text-2xl text-orange-500 flex items-center font-extrabold">
          <Image
            width={25}
            height={25}
            src="/carrot-logo.png"
            alt="carrot-logo"
            className="mr-4 ml-2"
          />
          Carrot
        </div>
      </Link>
    </div>
  );
}

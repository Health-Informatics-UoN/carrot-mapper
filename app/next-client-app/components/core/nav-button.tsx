"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Item } from "./nav-group";
import { Button } from "../ui/button";
import { cn } from "@/lib/utils";
import {
  LucideIcon,
  Waypoints,
  TableProperties,
  SearchCheck,
  Edit,
  FileScan,
  Download,
  Database,
  BookText,
} from "lucide-react";

export const NavButton = ({
  path,
  parallelRoutesKey,
  item,
}: {
  path: string;
  parallelRoutesKey?: string;
  item: Item;
}) => {
  const pathname = usePathname();
  const href = item.slug ? path + "/" + item.slug : path;
  const isActive = item.slug
    ? pathname === href || pathname.startsWith(href + "/")
    : (
        pathname === path ||
        pathname === path + "/" ||
        (item.matchPrefixes &&
          item.matchPrefixes.some(prefix =>
            pathname.startsWith(path + "/" + prefix)
          ))
      );
  const iconMap: { [key: string]: LucideIcon } = {
    SearchCheck,
    Waypoints,
    TableProperties,
    FileScan,
    Edit,
    Download,
    Database,
    BookText,
  };

  const Icon = item.iconName ? iconMap[item.iconName] : null;

  return (
    <Link href={href}>
      <Button
        variant="ghost"
        className={cn(
          isActive && "bg-muted"
        )}
      >
        {Icon && <Icon />}
        {item.text}
      </Button>
    </Link>
  );
};

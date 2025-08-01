"use client";

import Link from "next/link";
import { useSelectedLayoutSegment } from "next/navigation";
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
  const segment = useSelectedLayoutSegment(parallelRoutesKey);
  const href = item.slug ? path + "/" + item.slug : path;
  const isActive =
    // Example home pages e.g. `/layouts`
    (!item.slug && segment === null) ||
    segment === item.segment ||
    // Nested pages e.g. `/layouts/electronics`
    segment === item.slug;
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

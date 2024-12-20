import {
  BookMarked,
  Database,
  FileScan,
  Folders,
  Github,
  LogIn,
  LucideIcon,
  Upload,
} from "lucide-react";

export interface SidebarItems {
  links: Array<{
    label: string;
    href: string;
    icon?: LucideIcon;
  }>;
  routes: Array<{
    label: string;
    href: string;
    icon?: LucideIcon;
  }>;
}

export const sidebarItems: SidebarItems = {
  links: [
    { label: "Projects", href: "/projects/", icon: Folders },
    { label: "Datasets", href: "/datasets/", icon: Database },
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
  routes: [
    {
      label: "Documentation",
      href: "https://carrot4omop.ac.uk",
      icon: BookMarked,
    },
    {
      label: "GitHub",
      href: "https://github.com/Health-Informatics-UoN/Carrot-Mapper",
      icon: Github,
    },
  ],
};

import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "../ui/button";

interface SidebarButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: LucideIcon;
  children?: React.ReactNode;
  className?: string;
}

export function SidebarButton({
  icon: Icon,
  className,
  children,
  ...props
}: SidebarButtonProps) {
  return (
    <Button
      variant="ghost"
      className={cn(
        "gap-2 justify-start focus-visible:ring-0 dark:focus-visible:ring-offset-0",
        "hover:bg-muted hover:text-foreground transition-colors",
        "text-black dark:text-white",
        className
      )}
      {...props}
    >
      {Icon && <Icon size={20} />}
      <span>{children}</span>
    </Button>
  );
}

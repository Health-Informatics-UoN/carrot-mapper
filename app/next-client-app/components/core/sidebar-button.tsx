import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button, ButtonProps } from "../ui/button";

interface SidebarButtonProps extends ButtonProps {
  icon?: LucideIcon;
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
        className
      )}
      {...props}
    >
      {Icon && <Icon size={20} />}
      <span>{children}</span>
    </Button>
  );
}

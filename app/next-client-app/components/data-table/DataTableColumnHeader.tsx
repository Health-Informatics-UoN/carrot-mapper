import {
  ArrowDownIcon,
  ArrowUpIcon,
  CaretSortIcon,
  EyeNoneIcon,
} from "@radix-ui/react-icons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { Column } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { useRouter, useSearchParams } from "next/navigation";
import { navigateWithSearchParam } from "@/lib/client-utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/tooltip";

interface DataTableColumnHeaderProps<TData, TValue>
  extends React.HTMLAttributes<HTMLDivElement> {
  column: Column<TData, TValue>;
  title: string;
  sortName?: string;
  description?: string;
}

export function DataTableColumnHeader<TData, TValue>({
  column,
  title,
  sortName = "",
  className,
  description,
}: DataTableColumnHeaderProps<TData, TValue>) {
  const router = useRouter();
  const searchParams = useSearchParams();

  if (!column.getCanSort()) {
    return description ? (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className={cn(className)}>{title}</div>
          </TooltipTrigger>
          <TooltipContent className="bg-black text-white">
            <p>{description}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    ) : (
      <div className={cn(className)}>{title}</div>
    );
  }

  function getColumnSortState(): { sorted: boolean; type: string | null } {
    const ordering = searchParams.get("ordering");
    if (ordering && (ordering === sortName || ordering === `-${sortName}`)) {
      return { sorted: true, type: ordering.startsWith("-") ? "desc" : "asc" };
    }
    return { sorted: false, type: null };
  }

  const sortColumn = (sortName: string) => {
    navigateWithSearchParam("ordering", sortName, router, searchParams);
  };

  return (
    <div className={cn("flex items-center space-x-2", className)}>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="-ml-3 h-8 data-[state=open]:bg-accent"
          >
            <span>{title}</span>
            {getColumnSortState() ? (
              getColumnSortState().type === "desc" ? (
                <ArrowDownIcon className="ml-2 h-4 w-4" />
              ) : getColumnSortState().type === "asc" ? (
                <ArrowUpIcon className="ml-2 h-4 w-4" />
              ) : (
                <CaretSortIcon className="ml-2 h-4 w-4" />
              )
            ) : null}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuItem onClick={() => sortColumn(sortName)}>
            <ArrowUpIcon className="mr-2 h-3.5 w-3.5 text-muted-foreground/70" />
            Asc
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => sortColumn(`-${sortName}`)}>
            <ArrowDownIcon className="mr-2 h-3.5 w-3.5 text-muted-foreground/70" />
            Desc
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => column.toggleVisibility(false)}>
            <EyeNoneIcon className="mr-2 h-3.5 w-3.5 text-muted-foreground/70" />
            Hide
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

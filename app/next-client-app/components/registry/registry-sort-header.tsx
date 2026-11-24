import {
  ArrowDownIcon,
  ArrowUpIcon,
  CaretSortIcon,
  EyeNoneIcon,
} from "@radix-ui/react-icons";
import type { Column } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Sort } from "@/types/mapping-registry";

type RegistrySortHeaderProps<T> = {
  column: Column<T, unknown>;
  title: string;
  sortKey: string;
  sort: Sort;
  onSort: (sort: Sort) => void;
};

export function RegistrySortHeader<T>({
  column,
  title,
  sortKey,
  sort,
  onSort,
}: RegistrySortHeaderProps<T>) {
  const direction = sort?.key === sortKey ? sort.direction : null;

  return (
    <div className="flex items-center">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="-ml-3 h-11 whitespace-nowrap px-3 text-sm font-semibold sm:text-base data-[state=open]:bg-accent"
            aria-label={`Sort ${title}`}
          >
            <span>{title}</span>
            {direction === "asc" ? (
              <ArrowUpIcon className="ml-2 size-4" />
            ) : direction === "desc" ? (
              <ArrowDownIcon className="ml-2 size-4" />
            ) : (
              <CaretSortIcon className="ml-2 size-4" />
            )}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuItem
            onClick={() => onSort({ key: sortKey, direction: "asc" })}
          >
            <ArrowUpIcon className="mr-2 size-4 text-muted-foreground" /> Asc
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => onSort({ key: sortKey, direction: "desc" })}
          >
            <ArrowDownIcon className="mr-2 size-4 text-muted-foreground" /> Desc
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => column.toggleVisibility(false)}>
            <EyeNoneIcon className="mr-2 size-4 text-muted-foreground" /> Hide
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

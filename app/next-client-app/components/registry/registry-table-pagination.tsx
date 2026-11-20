import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PAGE_SIZE_OPTIONS } from "@/constants/mapping-registry";

type RegistryTablePaginationProps = {
  page: number;
  pageSize: number;
  count: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
};

export function RegistryTablePagination({
  page,
  pageSize,
  count,
  onPageChange,
  onPageSizeChange,
}: RegistryTablePaginationProps) {
  const numberOfPages = Math.max(1, Math.ceil(count / pageSize));
  const atStart = page <= 1;
  const atEnd = page >= numberOfPages;

  return (
    <div className="flex items-center justify-center pt-4">
      <div className="flex w-full flex-col-reverse items-center justify-end gap-4 overflow-auto p-1 sm:flex-row sm:gap-8">
        <div className="flex flex-col-reverse items-center gap-4 sm:flex-row sm:gap-6 lg:gap-8">
          <div className="flex items-center space-x-2">
            <p className="whitespace-nowrap text-sm font-medium">Rows per page</p>
            <Select value={String(pageSize)} onValueChange={(value) => onPageSizeChange(Number(value))}>
              <SelectTrigger className="h-8 w-18 bg-background text-foreground">
                <SelectValue placeholder={String(pageSize)} />
              </SelectTrigger>
              <SelectContent side="top" className="bg-popover">
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <SelectItem key={size} value={String(size)}>
                    {size}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-center text-sm font-medium">
            Page {page} of {numberOfPages}
          </div>
          <div className="flex items-center space-x-2">
            <Button type="button" variant="outline" aria-label="Go to first page" onClick={() => onPageChange(1)} disabled={atStart}>
              <ChevronsLeft className="size-4" aria-hidden="true" />
            </Button>
            <Button type="button" variant="outline" aria-label="Go to previous page" onClick={() => onPageChange(page - 1)} disabled={atStart}>
              <ChevronLeft className="size-4" aria-hidden="true" />
            </Button>
            <Button type="button" variant="outline" aria-label="Go to next page" onClick={() => onPageChange(page + 1)} disabled={atEnd}>
              <ChevronRight className="size-4" aria-hidden="true" />
            </Button>
            <Button type="button" variant="outline" aria-label="Go to last page" onClick={() => onPageChange(numberOfPages)} disabled={atEnd}>
              <ChevronsRight className="size-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

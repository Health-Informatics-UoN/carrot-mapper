import {
  ChevronLeftIcon,
  ChevronRightIcon,
  DoubleArrowLeftIcon,
  DoubleArrowRightIcon,
} from "@radix-ui/react-icons";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { useRouter, useSearchParams } from "next/navigation";
import { navigateWithSearchParam } from "@/lib/client-utils";

interface DataTablePaginationProps<TData> {
  count: number;
  defaultPageSize?: 10 | 20 | 30 | 40 | 50;
  pageSizeOptions?: number[];
}

export function DataTablePagination<TData>({
  count,
  defaultPageSize = 10,
  pageSizeOptions = [10, 20, 30, 40, 50],
}: DataTablePaginationProps<TData>) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const currentPage = Number(searchParams.get("p") ?? "1");
  const pageSize = Number(searchParams.get("page_size") ?? defaultPageSize);
  const numberOfPages = Math.max(Math.ceil(count / pageSize), 1);

  /*
Notice:
The condition below avoids the parent page to break when users change the page size to a larger number
which making the app couldn't find the data with the according p and page_size params in query URL.
If the user actually does this "rarely-happened" action, they will see a "No results" page,
then be pushed back to the first page with the page size they have chosen. An Error about Router in the console will also appear.
The more effective fix can be adding some logics in the API endpoint getting the data,
but it also means that we need to change many other API endpoints as well. So it may not be desirable.
*/
  if (currentPage > numberOfPages) {
    navigateWithSearchParam(
      "p",
      Math.ceil(count / pageSize),
      router,
      searchParams
    );
  }
  const changePageSize = (size: number) => {
    navigateWithSearchParam("page_size", size, router, searchParams);
  };

  const navigateToPage = (param: number) => {
    navigateWithSearchParam("p", param, router, searchParams);
  };

  const canNotGoToPreviousPage = (): boolean => {
    return currentPage === 1 || count < pageSize;
  };

  const canNotGoToNextPage = (): boolean => currentPage >= numberOfPages;

  return (
    <div className="flex w-full flex-col-reverse items-center justify-end gap-4 overflow-auto p-1 sm:flex-row sm:gap-8">
      <div className="flex flex-col-reverse items-center gap-4 sm:flex-row sm:gap-6 lg:gap-8">
        <div className="flex items-center space-x-2">
          <p className="whitespace-nowrap text-sm font-medium">Rows per page</p>
          <Select
            onValueChange={(value) => {
              changePageSize(Number(value));
            }}
          >
            <SelectTrigger className="h-8 w-[4.5rem] bg-background text-foreground">
              <SelectValue placeholder={pageSize} />
            </SelectTrigger>
            <SelectContent side="top">
              {pageSizeOptions.map((pageSize) => (
                <SelectItem key={pageSize} value={`${pageSize}`}>
                  {pageSize}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center justify-center text-sm font-medium">
          Page {currentPage} of {numberOfPages}
        </div>
        <div className="flex items-center space-x-2">
          <Button
            aria-label="Go to first page"
            className="size-8 p-0 flex"
            onClick={() => navigateToPage(1)}
            disabled={canNotGoToPreviousPage()}
          >
            <DoubleArrowLeftIcon className="size-4" aria-hidden="true" />
          </Button>
          <Button
            aria-label="Go to previous page"
            className="size-8 p-0 flex"
            onClick={() => navigateToPage(currentPage - 1)}
            disabled={canNotGoToPreviousPage()}
          >
            <ChevronLeftIcon className="size-4" aria-hidden="true" />
          </Button>
          <Button
            aria-label="Go to next page"
            className="size-8 p-0 flex"
            onClick={() => navigateToPage(currentPage + 1)}
            disabled={canNotGoToNextPage()}
          >
            <ChevronRightIcon className="size-4" aria-hidden="true" />
          </Button>
          <Button
            aria-label="Go to last page"
            className="size-8 p-0 flex"
            onClick={() => navigateToPage(numberOfPages)}
            disabled={canNotGoToNextPage()}
          >
            <DoubleArrowRightIcon className="size-4" aria-hidden="true" />
          </Button>
        </div>
      </div>
    </div>
  );
}

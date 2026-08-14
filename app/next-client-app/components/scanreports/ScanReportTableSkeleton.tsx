import { Skeleton } from "@/components/ui/skeleton";

/**
 * Generic fallback for the scan report tables/fields/values routes, shaped
 * like the DataTable they're loading instead of one blank full-page block.
 */
export function ScanReportTableSkeleton() {
  return (
    <div>
      <Skeleton className="h-4 w-64 mb-3" />
      <div className="flex justify-between items-center mb-3">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-9 w-24" />
      </div>
      <div className="rounded-md border">
        <div className="border-b p-3">
          <Skeleton className="h-4 w-full" />
        </div>
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="p-3 border-b last:border-b-0">
            <Skeleton className="h-4 w-full" />
          </div>
        ))}
      </div>
      <div className="flex items-center justify-center pt-4">
        <Skeleton className="h-8 w-64" />
      </div>
    </div>
  );
}

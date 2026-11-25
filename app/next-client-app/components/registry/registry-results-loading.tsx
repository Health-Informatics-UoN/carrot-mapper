import { Skeleton } from "@/components/ui/skeleton";

export function RegistryResultsLoading() {
  return (
    <div
      className="space-y-2 rounded-lg border p-4"
      role="status"
      aria-live="polite"
      aria-label="Loading search results"
    >
      <div className="mb-4 flex items-center justify-between">
        <Skeleton className="h-5 w-44" />
        <Skeleton className="h-5 w-20" />
      </div>
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="flex gap-3 border-t py-3">
          <Skeleton className="h-5 w-1/4" />
          <Skeleton className="h-5 w-1/3" />
          <Skeleton className="h-5 w-1/5" />
        </div>
      ))}
      <span className="sr-only">Loading matching records</span>
    </div>
  );
}

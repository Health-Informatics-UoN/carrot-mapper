import { Database } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { RegistryStats } from "@/types/mapping-registry";

type RegistryDataContentProps = { stats: RegistryStats };

export function RegistryDataContent({ stats }: RegistryDataContentProps) {
  return (
    <aside
      className="w-full rounded-lg border bg-card px-4 py-3 shadow-sm sm:w-auto"
      aria-label="Data Content — demo statistics"
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="flex items-center gap-2 text-sm font-semibold">
          <Database className="size-4" /> Data Content
        </span>
        <Badge variant="outline" className="text-[10px]">Demo</Badge>
      </div>
      <dl className="grid grid-cols-3 gap-x-5 gap-y-1 text-xs sm:gap-x-6">
        <div>
          <dt className="whitespace-nowrap text-muted-foreground">Release date</dt>
          <dd className="mt-1 whitespace-nowrap font-semibold">{stats.releaseDate}</dd>
        </div>
        <div>
          <dt className="whitespace-nowrap text-muted-foreground">Total mappings</dt>
          <dd className="mt-1 text-base font-semibold tabular-nums">{stats.totalMappings}</dd>
        </div>
        <div>
          <dt className="whitespace-nowrap text-muted-foreground">Total sets</dt>
          <dd className="mt-1 text-base font-semibold tabular-nums">{stats.totalSets}</dd>
        </div>
      </dl>
    </aside>
  );
}

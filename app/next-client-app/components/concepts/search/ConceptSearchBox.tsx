"use client";

import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useDebouncedCallback } from "use-debounce";

export function ConceptSearchBox() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleSearch = useDebouncedCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const query = event.target.value;
      const params = new URLSearchParams(Array.from(searchParams.entries()));
      if (query) {
        params.set("q", query);
      } else {
        params.delete("q");
      }
      // A new query invalidates the current page of results.
      params.delete("search_p");
      router.push(`?${params.toString()}`, { scroll: false });
    },
    300,
  );

  return (
    <div className="relative max-w-sm w-full">
      <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
      <Input
        placeholder="Search concepts by name, code, or synonym..."
        defaultValue={searchParams.get("q") ?? ""}
        onChange={handleSearch}
        className="pl-8"
      />
    </div>
  );
}

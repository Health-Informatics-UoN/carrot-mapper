import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useTypewriterPlaceholder } from "@/lib/hooks/use-typewriter-placeholder";
import { SEARCH_EXAMPLES, SEARCH_FIELDS, SET_SEARCH_FIELDS } from "@/constants/mapping-registry";
import type { SearchField, View } from "@/types/mapping-registry";

type RegistrySearchBarProps = {
  view: View;
  field: SearchField;
  query: string;
  isLoading: boolean;
  onFieldChange: (field: SearchField) => void;
  onQueryChange: (query: string) => void;
};

export function RegistrySearchBar({
  view,
  field,
  query,
  isLoading,
  onFieldChange,
  onQueryChange,
}: RegistrySearchBarProps) {
  const example = useTypewriterPlaceholder(SEARCH_EXAMPLES[field]);
  const fieldOptions = view === "mappings" ? SEARCH_FIELDS : SET_SEARCH_FIELDS;
  const hasQuery = query.trim().length > 0;

  return (
    <div className="space-y-2">
      <div className="flex flex-col gap-2 rounded-xl border bg-background p-2 shadow-sm sm:flex-row">
        <Select value={field} onValueChange={(value) => onFieldChange(value as SearchField)}>
          <SelectTrigger aria-label="Search by" className="w-full shrink-0 sm:w-48">
            <SelectValue placeholder="Search by" />
          </SelectTrigger>
          <SelectContent>
            {fieldOptions.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <label className="sr-only" htmlFor="registry-search">
          Search published Registry content
        </label>
        <div className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="registry-search"
            type="text"
            autoComplete="off"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder={`Try ${example}${query ? "" : "|"}`}
            className="pl-9 pr-10"
          />
          {query && (
            <button
              type="button"
              aria-label="Clear search text"
              onClick={() => onQueryChange("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
            >
              <X className="size-4" />
            </button>
          )}
        </div>
        <div className="flex items-center justify-center px-2 text-xs text-muted-foreground sm:whitespace-nowrap">
          <span>Live search</span>
        </div>
      </div>
      {hasQuery && (
        <p className="text-center text-xs text-muted-foreground" role="status">
          {isLoading ? "Searching..." : "Results update as you type"}
        </p>
      )}
    </div>
  );
}

import { useCallback, useEffect, useMemo, useState } from "react";
import { DEFAULT_PAGE_SIZE, SEARCH_DEBOUNCE_MS } from "@/constants/mapping-registry";
import {
  matchesMapping,
  matchesMappingSet,
  paginate,
  sortRecords,
} from "@/lib/registry/client-search";
import { MOCK_MAPPINGS, MOCK_MAPPING_SETS, MOCK_STATS } from "@/lib/registry/mock-data";
import type { Mapping, MappingSet, SearchField, Sort, View } from "@/types/mapping-registry";

type DebouncedSearch = { query: string; field: SearchField; view: View };

/**
 * All state for the Registry page: what's being searched, which view is open,
 * paging, sorting, and the resulting records.
 *
 * The return shape is the contract with page.tsx and the components. The
 * integration PR changes how records are fetched inside this hook, not what it returns.
 */
export function useRegistrySearch() {
  const [view, setView] = useState<View>("mappings");
  const [field, setField] = useState<SearchField>("sourceTerm");
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState<DebouncedSearch>({
    query: "",
    field: "sourceTerm",
    view: "mappings",
  });
  const [browseAll, setBrowseAll] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [sort, setSort] = useState<Sort>(null);

  // Simulated async search so the loading state can be reviewed in the UI PR.
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebounced({ query: query.trim(), field, view });
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query, field, view]);

  const trimmedQuery = query.trim();
  const hasQuery = trimmedQuery.length > 0;
  const showResults = browseAll || hasQuery;
  const isLoading =
    hasQuery &&
    (trimmedQuery !== debounced.query || field !== debounced.field || view !== debounced.view);
  const activeQuery = hasQuery ? debounced.query : "";


/* Replace this block with Registry API requests; */

  const filteredMappings = useMemo(
    () => sortRecords(MOCK_MAPPINGS.filter((m) => matchesMapping(m, field, activeQuery)), sort),
    [field, activeQuery, sort],
  );

  const filteredMappingSets = useMemo(
    () => sortRecords(MOCK_MAPPING_SETS.filter((s) => matchesMappingSet(s, field, activeQuery)), sort),
    [field, activeQuery, sort],
  );

  // The mapping set a mapping was published in.
  const setForMapping = useCallback(
    (mapping: Mapping): MappingSet | null =>
      MOCK_MAPPING_SETS.find(
        (set) =>
          set.title === mapping.mappingSet &&
          set.version === mapping.mappingSetVersion &&
          set.publisher === mapping.publisher,
      ) ?? null,
    [],
  );

  const stats = MOCK_STATS;

  const total = view === "mappings" ? filteredMappings.length : filteredMappingSets.length;
  const mappings = useMemo(
    () => paginate(filteredMappings, page, pageSize),
    [filteredMappings, page, pageSize],
  );
  const mappingSets = useMemo(
    () => paginate(filteredMappingSets, page, pageSize),
    [filteredMappingSets, page, pageSize],
  );

  function changeField(nextField: SearchField) {
    setField(nextField);
    setPage(1);
    setSort(null);
  }

  function changeQuery(nextQuery: string) {
    setQuery(nextQuery);
    setPage(1);
  }

  function changePageSize(size: number) {
    setPageSize(size);
    setPage(1);
  }

  function browse(nextView: View) {
    setQuery("");
    setView(nextView);
    setField(nextView === "sets" ? "mappingSet" : "sourceTerm");
    setBrowseAll(true);
    setPage(1);
    setSort(null);
  }

  function chooseView(nextView: View) {
    if (nextView === view) return;
    browse(nextView);
  }

  function reset() {
    setQuery("");
    setField("sourceTerm");
    setView("mappings");
    setBrowseAll(false);
    setPage(1);
    setPageSize(DEFAULT_PAGE_SIZE);
    setSort(null);
  }

  return {
    view,
    field,
    query,
    page,
    pageSize,
    sort,
    showResults,
    isLoading,
    mappings,
    mappingSets,
    total,
    stats,
    changeField,
    changeQuery,
    changePageSize,
    setPage,
    setSort,
    browse,
    chooseView,
    reset,
    setForMapping,
  };
}

export type RegistrySearch = ReturnType<typeof useRegistrySearch>;

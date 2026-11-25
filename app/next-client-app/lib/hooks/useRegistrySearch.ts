import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  DEFAULT_PAGE_SIZE,
  PAGE_SIZE_OPTIONS,
  SEARCH_DEBOUNCE_MS,
  SEARCH_FIELDS,
  SET_SEARCH_FIELDS,
} from "@/constants/mapping-registry";
import {
  matchesMapping,
  matchesMappingSet,
  paginate,
  sortRecords,
} from "@/lib/registry/client-search";
import {
  getMappingSetById,
  MOCK_MAPPINGS,
  MOCK_MAPPING_SETS,
  MOCK_STATS,
} from "@/lib/registry/mock-data";
import type {
  Mapping,
  MappingSet,
  SearchField,
  Sort,
  View,
} from "@/types/mapping-registry";

export function useRegistrySearch(view: View = "mappings") {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const validFields = (
    view === "mappings" ? SEARCH_FIELDS : SET_SEARCH_FIELDS
  ).map((field) => field.value);
  const rawQuery = searchParams.get("q") ?? "";
  const urlField = searchParams.get("field") as SearchField | null;
  const field =
    urlField && validFields.includes(urlField)
      ? urlField
      : ((view === "mappings" ? "sourceTerm" : "mappingSet") as SearchField);

  const rawPage = Number(searchParams.get("p"));
  const page = Number.isInteger(rawPage) && rawPage >= 1 ? rawPage : 1;
  const rawPageSize = Number(searchParams.get("page_size"));
  const pageSize = PAGE_SIZE_OPTIONS.includes(rawPageSize)
    ? rawPageSize
    : DEFAULT_PAGE_SIZE;

  const rawSort = searchParams.get("ordering");
  const sortKeys =
    view === "mappings"
      ? new Set([
          "sourceTerm",
          "targetConcept",
          "conceptId",
          "vocabulary",
          "publisher",
          "mappingSet",
          "mappingSetVersion",
          "canonicalIri",
          "license",
          "predicate",
          "justification",
          "publishedAt",
        ])
      : new Set(["title", "publisher", "version", "license", "publishedAt"]);
  let sort: Sort = null;
  if (rawSort) {
    const direction = rawSort.startsWith("-") ? "desc" : "asc";
    const key = direction === "desc" ? rawSort.slice(1) : rawSort;
    if (sortKeys.has(key)) sort = { key, direction };
  }

  const [inputQuery, setInputQuery] = useState(rawQuery);
  const lastWrittenQueryRef = useRef(rawQuery);

  useEffect(() => {
    if (rawQuery !== lastWrittenQueryRef.current) {
      setInputQuery(rawQuery);
    }
    lastWrittenQueryRef.current = rawQuery;
  }, [rawQuery]);

  const pushUrl = useCallback(
    (
      updates: Record<string, string | number | null>,
      method: "push" | "replace" = "push",
    ) => {
      const params = new URLSearchParams(searchParams.toString());
      Object.entries(updates).forEach(([key, value]) => {
        if (
          value === null ||
          value === "" ||
          (key === "p" && value === 1) ||
          (key === "page_size" && value === DEFAULT_PAGE_SIZE)
        ) {
          params.delete(key);
        } else {
          params.set(key, String(value));
        }
      });
      const queryString = params.toString();
      const url = queryString ? `${pathname}?${queryString}` : pathname;
      if (method === "replace") router.replace(url, { scroll: false });
      else router.push(url, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  useEffect(() => {
    if (inputQuery.trim() === rawQuery.trim()) return;
    const timer = setTimeout(() => {
      const nextQuery = inputQuery.trim();
      lastWrittenQueryRef.current = nextQuery;
      pushUrl({ q: nextQuery || null, p: 1 }, "replace");
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [inputQuery, rawQuery, pushUrl]);

  const activeQuery = rawQuery.trim();
  const isLoading = inputQuery.trim() !== rawQuery.trim();

  const filteredMappings = useMemo(
    () =>
      sortRecords(
        MOCK_MAPPINGS.filter((m) => matchesMapping(m, field, activeQuery)),
        sort,
      ),
    [field, activeQuery, sort],
  );
  const filteredMappingSets = useMemo(
    () =>
      sortRecords(
        MOCK_MAPPING_SETS.filter((s) =>
          matchesMappingSet(s, field, activeQuery),
        ),
        sort,
      ),
    [field, activeQuery, sort],
  );
  const setForMapping = useCallback(
    (mapping: Mapping): MappingSet | null =>
      getMappingSetById(mapping.mappingSetId),
    [],
  );

  const stats = MOCK_STATS;
  const total =
    view === "mappings" ? filteredMappings.length : filteredMappingSets.length;
  const mappings = useMemo(
    () => paginate(filteredMappings, page, pageSize),
    [filteredMappings, page, pageSize],
  );
  const mappingSets = useMemo(
    () => paginate(filteredMappingSets, page, pageSize),
    [filteredMappingSets, page, pageSize],
  );

  function changeField(nextField: SearchField) {
    pushUrl({
      field:
        nextField === (view === "mappings" ? "sourceTerm" : "mappingSet")
          ? null
          : nextField,
      p: 1,
    });
  }
  function changeQuery(nextQuery: string) {
    setInputQuery(nextQuery);
  }
  return {
    view,
    field,
    query: inputQuery,
    page,
    pageSize,
    isLoading,
    mappings,
    mappingSets,
    total,
    stats,
    changeField,
    changeQuery,
    setForMapping,
  };
}

export type RegistrySearch = ReturnType<typeof useRegistrySearch>;

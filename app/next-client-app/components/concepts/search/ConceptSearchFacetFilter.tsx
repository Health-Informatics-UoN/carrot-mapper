"use client";

import { FacetsFilter } from "@/components/scanreports/FacetsFilter";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

interface ConceptSearchFacetFilterProps {
  title: string;
  param: ConceptSearchFacetParam;
  counts: Record<string, number>;
}

export function ConceptSearchFacetFilter({
  title,
  param,
  counts,
}: ConceptSearchFacetFilterProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const options: FilterOption[] = Object.entries(counts)
    .sort(([, a], [, b]) => b - a)
    .map(([value, count]) => ({ label: `${value} (${count})`, value }));

  const [selectedOptions, setSelectedOptions] = useState<FilterOption[]>([]);

  useEffect(() => {
    const paramValue = searchParams.get(param);
    if (!paramValue) {
      setSelectedOptions([]);
      return;
    }
    const values = paramValue.split(",");
    setSelectedOptions(
      values.map((value) => {
        const known = options.find((option) => option.value === value);
        return known ?? { label: value, value };
      }),
    );
    // Only re-sync from the URL, not on every `options` (facet-count) refresh.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, param]);

  const commitSelection = (updated: FilterOption[]) => {
    const params = new URLSearchParams(Array.from(searchParams.entries()));
    if (updated.length > 0) {
      params.set(param, updated.map((option) => option.value).join(","));
    } else {
      params.delete(param);
    }
    params.delete("search_p");
    router.push(`?${params.toString()}`, { scroll: false });
  };

  const handleSelect = (option: FilterOption) => {
    const isSelected = selectedOptions.some(
      (item) => item.value === option.value,
    );
    const updated = isSelected
      ? selectedOptions.filter((item) => item.value !== option.value)
      : [...selectedOptions, option];
    setSelectedOptions(updated);
    commitSelection(updated);
  };

  const handleClear = () => {
    setSelectedOptions([]);
    commitSelection([]);
  };

  return (
    <FacetsFilter
      title={title}
      options={options}
      selectedOptions={selectedOptions}
      handleSelect={handleSelect}
      handleClear={handleClear}
    />
  );
}

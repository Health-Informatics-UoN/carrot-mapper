"use client";

import { FacetsFilter } from "@/components/scanreports/FacetsFilter";
import { navigateWithSearchParam } from "@/lib/client-utils";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { DataTableFilter } from "../data-table/DataTableFilter";

const ConceptDataOptions = [
    {
      label: "Reused",
      value: "R",
      color: "text-emerald-900 dark:text-emerald-600",
    },
    {
      label: "Manual",
      value: "M",
      color: "text-blue-900 dark:text-blue-600",
    },
    {
      label: "Vocab",
      value: "V",
      color: "text-pink-900 dark:text-pink-600",
    },
]

export function ConceptDataFilter() {
  const router = useRouter();
  const searchParam = useSearchParams();

  const [selectedOptions, setOptions] = useState<FilterOption[]>();

  // Runs on load to populate the selectedOptions from params
  useEffect(() => {
    const creationTypeParam = searchParam.get("creation_type");
    if (creationTypeParam) {
      const creationTypeValues = creationTypeParam.split(",");
      const filteredOptions = ConceptDataOptions.filter((option) =>
        creationTypeValues.includes(option.value)
      );
      setOptions(filteredOptions);
    }
  }, [searchParam]);

  const handleSelectOption = (option: FilterOption) => {
    const updatedOptions = selectedOptions ? [...selectedOptions] : [];
    const isSelected = updatedOptions.some(
      (item) => item.value === option.value
    );

    if (isSelected) {
      // Remove if it's already selected
      const index = updatedOptions.findIndex(
        (item) => item.value === option.value
      );
      updatedOptions.splice(index, 1);
    } else {
      updatedOptions.push(option);
    }

    setOptions(updatedOptions);
    handleFacetsFilter(updatedOptions);
  };

  const handleFacetsFilter = (options?: FilterOption[]) => {
    if (options?.length === 0) {
      navigateWithSearchParam(
        "creation_type",
        "",
        router,
        searchParam
      );
      return;
    }
    navigateWithSearchParam(
      "creation_type",
      options?.map((option) => option.value).join(",") || "",
      router,
      searchParam
    );
  };

  return (
    <div className="flex gap-4 max-sm:hidden">
        <DataTableFilter filter="value" filterText="Value" />
        <FacetsFilter
        title="Concepts"
        options={ConceptDataOptions}
        selectedOptions={selectedOptions}
        handleSelect={handleSelectOption}
        handleClear={() => (setOptions([]), handleFacetsFilter())}
        />
    </div>
  );
}

"use client";

import { FacetsFilter } from "@/components/scanreports/FacetsFilter";
import { MappingStatusOptions } from "@/constants/scanReportStatus";
import { navigateWithSearchParam } from "@/lib/client-utils";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

export function MappingStatusFilter() {
  const router = useRouter();
  const searchParam = useSearchParams();

  const [selectedOptions, setOptions] = useState<FilterOption[]>();

  // Runs on load to populate the selectedOptions from params
  useEffect(() => {
    const statusParam = searchParam.get("mapping_status__value__in");
    if (statusParam) {
      const statusValues = statusParam.split(",");
      const filteredOptions = MappingStatusOptions.filter((option) =>
        statusValues.includes(option.value)
      );
      setOptions(filteredOptions);
    }
  }, []);

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
    navigateWithSearchParam(
      "mapping_status__value__in",
      options?.map((option) => option.value) || "",
      router,
      searchParam
    );
  };

  return (
    <div className="max-sm:hidden">
      <FacetsFilter
        title="Mapping Status"
        options={MappingStatusOptions}
        selectedOptions={selectedOptions}
        handleSelect={handleSelectOption}
        handleClear={() => (setOptions([]), handleFacetsFilter())}
      />
    </div>
  );
}

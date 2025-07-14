"use client";

import { FacetsFilter } from "@/components/scanreports/FacetsFilter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { UploadStatusOptions } from "@/constants/scanReportStatus";
import { navigateWithSearchParam } from "@/lib/client-utils";
import { FilterOption } from "@/types/filter";
import { Upload } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useDebouncedCallback } from "use-debounce";
import { MappingStatusFilter } from "./MappingStatusFilter";

export function ScanReportsTableFilter({
  filter,
  filterText,
}: {
  filter: string;
  filterText: string;
}) {
  const router = useRouter();
  const searchParam = useSearchParams();

  const [selectedOptions, setOptions] = useState<FilterOption[]>();

  // Runs on load to populate the selectedOptions from params
  useEffect(() => {
    const statusParam = searchParam.get("upload_status__value__in");
    if (statusParam) {
      const statusValues = statusParam.split(",");
      const filteredOptions = UploadStatusOptions.filter((option) =>
        statusValues.includes(option.value)
      );
      setOptions(filteredOptions);
    }
  }, []);

  const handleFilter = useDebouncedCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const query = event.target.value;
      if (query.length > 2) {
        navigateWithSearchParam(
          `${filter}__icontains`,
          query,
          router,
          searchParam
        );
      } else if (query.length === 0) {
        // Handle resetting the filter
        navigateWithSearchParam(
          `${filter}__icontains`,
          "",
          router,
          searchParam
        );
      }
    },
    300
  );

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
      "upload_status__value__in",
      options?.map((option) => option.value) || "",
      router,
      searchParam
    );
  };

  return (
    <div className="flex w-full justify-between">
      <div className="flex gap-4">
        <Input
          placeholder={`Filter by ${filterText}...`}
          onChange={handleFilter}
          className="w-[250px]"
        />

        <div className="max-sm:hidden">
          <FacetsFilter
            title="Upload Status"
            options={UploadStatusOptions}
            selectedOptions={selectedOptions}
            handleSelect={handleSelectOption}
            handleClear={() => (setOptions([]), handleFacetsFilter())}
          />
        </div>
        <MappingStatusFilter />
      </div>
      <div>
        <Link href="/scanreports/create" prefetch={false}>
          <Button variant={"outline-solid"} className="ml-auto mr-4">
            <Upload className="mr-2 h-4 w-4" />
            Upload Scan Report
          </Button>
        </Link>
      </div>
    </div>
  );
}

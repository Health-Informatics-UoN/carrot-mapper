export const UploadStatusOptions = [
  {
    label: "Upload Complete",
    icon: "Check",
    value: "COMPLETE",
    color: "text-green-600 dark:text-green-600",
  },
  {
    label: "Upload Failed",
    icon: "X",
    value: "FAILED",
    color: "text-red-500 dark:text-red-500",
  },
  {
    label: "Upload In Progress",
    icon: "Loader2",
    value: "IN_PROGRESS",
    color: "text-orange-500 dark:text-orange-500",
  },
];

export const MappingStatusOptions = [
  {
    label: "Blocked",
    value: "BLOCKED",
    color: "text-red-900 dark:text-red-600",
  },
  {
    label: "Mapping Complete",
    value: "COMPLETE",
    color: "text-green-600 dark:text-green-600",
  },
  {
    label: "Pending Mapping",
    value: "PENDING",
    color: "text-blue-500 dark:text-blue-500",
  },
  {
    label: "Mapping 25%",
    value: "MAPPING_25PERCENT",
    color: "text-orange-300 dark:text-orange-300",
  },
  {
    label: "Mapping 50%",
    value: "MAPPING_50PERCENT",
    color: "text-orange-400 dark:text-orange-400",
  },
  {
    label: "Mapping 75%",
    value: "MAPPING_75PERCENT",
    color: "text-orange-500 dark:text-orange-500",
  },
];

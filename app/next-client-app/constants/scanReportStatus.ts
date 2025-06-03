export const UploadStatusOptions = [
  {
    label: "Upload Complete",
    icon: "Check",
    value: "COMPLETE",
    color: "text-success-foreground",
  },
  {
    label: "Upload Failed",
    icon: "X",
    value: "FAILED",
    color: "text-destructive",
  },
  {
    label: "Upload In Progress",
    icon: "Loader2",
    value: "IN_PROGRESS",
    color: "text-accent-foreground",
  },
];

export const MappingStatusOptions = [
  {
    label: "Blocked",
    value: "BLOCKED",
    color: "text-destructive",
  },
  {
    label: "Mapping Complete",
    value: "COMPLETE",
    color: "text-success-foreground",
  },
  {
    label: "Pending Mapping",
    value: "PENDING",
    color: "text-primary-foreground",
  },
  {
    label: "Mapping 25%",
    value: "MAPPING_25PERCENT",
    color: "text-accent-foreground",
  },
  {
    label: "Mapping 50%",
    value: "MAPPING_50PERCENT",
    color: "text-accent-foreground",
  },
  {
    label: "Mapping 75%",
    value: "MAPPING_75PERCENT",
    color: "text-accent-foreground",
  },
];

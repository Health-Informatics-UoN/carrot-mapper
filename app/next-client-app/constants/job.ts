export const JobStage = [
  { id: 1, value: "UPLOAD_SCAN_REPORT", display_name: "Upload Scan Report" },
  {
    id: 2,
    value: "BUILD_CONCEPTS_FROM_DICT",
    display_name: "Building concepts from OMOP Data dictionary",
  },
  {
    id: 3,
    value: "REUSE_CONCEPTS",
    display_name: "Reusing mappings from available data",
  },
  {
    id: 4,
    value: "GENERATE_RULES",
    display_name: "Generating rules from available mappings",
  },
  {
    id: 5,
    value: "GENERATE_AI_RECOMMENDATIONS",
    display_name: "Generate AI-powered mapping recommendations",
  },
  {
    id: 6,
    value: "DOWNLOAD_RULES",
    display_name: "Generate mapping rules file",
  },
];

export const StageStatus = [
  {
    label: "Not Started",
    icon: "CircleSlash",
    value: "NOT_STARTED",
    color: "text-muted-foreground",
  },
  {
    label: "Job Queued",
    icon: "CircleSlash",
    value: "QUEUED",
    color: "text-muted-foreground",
  },
  {
    label: "Job Complete",
    icon: "Check",
    value: "COMPLETE",
    color: "text-green-600",
  },
  {
    label: "Job Failed",
    icon: "X",
    value: "FAILED",
    color: "text-red-500",
  },
  {
    label: "Job In Progress",
    icon: "Loader2",
    value: "IN_PROGRESS",
    color: "text-orange-600",
  },
];

export const GeneralStatus = [
  {
    label:
      "Not Started or No data yet. Start by update table's Person ID and Date event",
    icon: "CircleSlash",
    value: "NOT_STARTED",
    color: "text-muted-foreground",
  },
  {
    label: "Complete. Click for details.",
    icon: "Check",
    value: "COMPLETE",
    color: "text-green-600",
  },
  {
    label: "Failed. Click for details.",
    icon: "X",
    value: "FAILED",
    color: "text-red-500",
  },
  {
    label: "In Progress. Click for details.",
    icon: "Loader2",
    value: "IN_PROGRESS",
    color: "text-orange-600",
  },
];

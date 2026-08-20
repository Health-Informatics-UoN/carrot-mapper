type ActivityLogScopeType = "scanreport" | "dataset";

type ActivityLogVerb =
  | "scanreport.uploaded"
  | "scanreport.updated"
  | "dataset.updated"
  | "mapping.added"
  | "mapping.deleted"
  | "rules.export_requested"
  | "rules.downloaded"
  | "automap.ran";

interface ActivityLog {
  id: number;
  scope_type: ActivityLogScopeType;
  scope_id: number;
  verb: ActivityLogVerb;
  occurred_at: string;
  actor_id: number | null;
  actor_label: string;
  object_type: string;
  object_id: number | null;
  detail: Record<string, string | number | boolean | string[] | null>;
  // Resolved server-side; only populated when scope_type is "scanreport".
  scan_report_name: string | null;
}

export const ACTIVITY_LOG_VERB_LABELS: Record<ActivityLogVerb, string> = {
  "scanreport.uploaded": "Scan report uploaded",
  "scanreport.updated": "Scan report updated",
  "dataset.updated": "Dataset updated",
  "mapping.added": "Mapping added",
  "mapping.deleted": "Mapping deleted",
  "rules.export_requested": "Rules export requested",
  "rules.downloaded": "Rules downloaded",
  "automap.ran": "Auto mapping ran",
};

function formatRoleChanges(
  detail: ActivityLog["detail"],
  role: string,
  label: string,
): string[] {
  const parts: string[] = [];
  const added = detail[`${role}_added`];
  const removed = detail[`${role}_removed`];
  if (Array.isArray(added) && added.length) {
    parts.push(`+${label}: ${added.join(", ")}`);
  }
  if (Array.isArray(removed) && removed.length) {
    parts.push(`-${label}: ${removed.join(", ")}`);
  }
  return parts;
}

function describeUpdateDetail(
  detail: ActivityLog["detail"],
  fields: { key: string; label: string }[],
  roles: { key: string; label: string }[],
): string {
  const parts: string[] = [];

  const { name_from, name_to } = detail;
  if (name_from && name_to && name_from !== name_to) {
    parts.push(`Renamed "${name_from}" → "${name_to}"`);
  }

  fields.forEach(({ key, label }) => {
    const from = detail[`${key}_from`];
    const to = detail[`${key}_to`];
    if (from && to && from !== to) {
      parts.push(`${label}: ${from} → ${to}`);
    }
  });

  roles.forEach(({ key, label }) =>
    parts.push(...formatRoleChanges(detail, key, label)),
  );

  return parts.join("; ");
}

export function describeActivityLogDetail(log: ActivityLog): string {
  switch (log.verb) {
    case "scanreport.uploaded":
      return log.detail.file_name ? `File: ${log.detail.file_name}` : "";
    case "scanreport.updated":
      return describeUpdateDetail(
        log.detail,
        [
          { key: "visibility", label: "Visibility" },
          { key: "author", label: "Author" },
          { key: "mapping_status", label: "Status" },
        ],
        [
          { key: "viewers", label: "Viewers" },
          { key: "editors", label: "Editors" },
        ],
      );
    case "dataset.updated":
      return describeUpdateDetail(
        log.detail,
        [{ key: "visibility", label: "Visibility" }],
        [
          { key: "admins", label: "Admins" },
          { key: "viewers", label: "Viewers" },
          { key: "editors", label: "Editors" },
        ],
      );
    case "mapping.added":
    case "mapping.deleted": {
      const { concept_name, table_name, field_name } = log.detail;
      const location = [table_name, field_name].filter(Boolean).join(" / ");
      if (!concept_name) return "";
      return location ? `${concept_name} (${location})` : String(concept_name);
    }
    case "rules.export_requested":
      return log.detail.file_type ? `Requested: ${log.detail.file_type}` : "";
    case "rules.downloaded":
      return log.detail.file_name ? `File: ${log.detail.file_name}` : "";
    case "automap.ran":
      return log.detail.table_name ? `Table: ${log.detail.table_name}` : "";
    default:
      return "";
  }
}

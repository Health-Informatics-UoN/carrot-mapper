import Link from "next/link";
import { Info } from "lucide-react";
import { getTableFieldMappings } from "@/api/scanreports";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

// On a field's values page: explains that the field's values fill one concept
// field of a note / note_nlp record (e.g. note_type -> note_class_concept_id),
// so they're mapped differently from values that create records.
export async function ValueMappedFieldNotice({
  scanReportId,
  table,
  fieldId,
}: {
  scanReportId: string;
  table: ScanReportTable;
  fieldId: string;
}) {
  if (table.table_role !== "note" && table.table_role !== "note_nlp") {
    return null;
  }
  const fieldMappings = await getTableFieldMappings(scanReportId, table.id);
  const mapping = fieldMappings?.mappings.find(
    (m) => m.map_values && m.source_field?.toString() === fieldId,
  );
  if (!mapping) {
    return null;
  }
  const record = table.table_role === "note" ? "note" : "note_nlp record";

  return (
    <Alert className="mb-4">
      <Info className="h-4 w-4" />
      <AlertTitle>
        These values fill <code>{mapping.omop_field}</code>
      </AlertTitle>
      <AlertDescription>
        <p>
          Map each value to the one concept it stands for. Each {record} gets
          the concept its value is mapped to, of any domain, and these concepts
          don&apos;t create records of their own. Values without a concept give
          0 (no matching concept).
        </p>
        <p className="mt-1">
          {mapping.values_mapped} of {mapping.values_total} values mapped.{" "}
          <Link
            className="underline underline-offset-4"
            href={`/scanreports/${scanReportId}/tables/${table.id}/update`}
          >
            Table settings
          </Link>
        </p>
      </AlertDescription>
    </Alert>
  );
}

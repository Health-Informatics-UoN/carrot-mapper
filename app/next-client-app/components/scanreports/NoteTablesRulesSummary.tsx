import Link from "next/link";
import { Settings } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { NoteTableExportStatus } from "./NoteTableExportStatus";

const ROLE_LABELS: Record<NoteTableSummary["table_role"], string> = {
  note: "Notes → note",
  note_nlp: "NLP terms → note_nlp",
};

// How one field of a note / note_nlp record is filled, in words
function describe(mapping: TableFieldMapping): string {
  if (mapping.vocabulary_id) {
    return `${mapping.vocabulary_id} codes in ${mapping.source_field_name}, each looked up by Carrot Transform`;
  }
  if (mapping.map_values) {
    return `concepts mapped to the values of ${mapping.source_field_name}`;
  }
  if (mapping.source_field_name) {
    return mapping.source_field_name;
  }
  const name = mapping.concept_name ? ` (${mapping.concept_name})` : "";
  return `always ${mapping.constant_value}${name}`;
}

// On the rules page: the note and note_nlp tables, whose records are built from
// table settings rather than from the mapping rules listed below them.
export function NoteTablesRulesSummary({
  scanReportId,
  tables,
}: {
  scanReportId: string;
  tables: NoteTableSummary[];
}) {
  if (tables.length === 0) {
    return null;
  }
  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="text-xl">Note tables</CardTitle>
        <CardDescription>
          Notes and NLP terms are built from each table&apos;s settings rather
          than from mapping rules, so they&apos;re listed here instead of in the
          rules below. They&apos;re included in the JSON v2 download. Concepts
          mapped on an NLP table also appear below, as the rules for their
          note_nlp records and the records derived from them.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {tables.map((table) => (
          <section key={table.id} className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="font-semibold">{table.name}</h4>
              <Badge variant="outline">{ROLE_LABELS[table.table_role]}</Badge>
              {table.export_problems.length === 0 ? (
                <Badge>In the rules</Badge>
              ) : (
                <Badge variant="destructive">Needs attention</Badge>
              )}
              <Link
                href={`/scanreports/${scanReportId}/tables/${table.id}/update`}
                className="ml-auto"
              >
                <Button variant="outline" size="sm">
                  <Settings className="h-4 w-4" />
                  Table settings
                </Button>
              </Link>
            </div>
            <NoteTableExportStatus
              problems={table.export_problems}
              scanReportId={scanReportId}
              tableId={table.id}
            />
            {table.mappings.length > 0 && (
              <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
                {table.mappings.map((mapping) => (
                  <div key={mapping.omop_field} className="contents">
                    <dt className="font-mono">{mapping.omop_field}</dt>
                    <dd className="text-muted-foreground">
                      {describe(mapping)}
                    </dd>
                  </div>
                ))}
              </dl>
            )}
          </section>
        ))}
      </CardContent>
    </Card>
  );
}

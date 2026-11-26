"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Save } from "lucide-react";
import { toast } from "sonner";
import { updateTableFieldMappings } from "@/api/scanreports";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ConceptIdInput } from "./ConceptIdInput";

type Mode = "source" | "values" | "constant" | "none";

interface Row {
  mode: Mode;
  sourceField: string; // field id, as a string for the select
  constant: string;
  conceptName: string | null;
  // As saved, for "values": the column and how many of its values are mapped
  saved?: { sourceField: string; total: number; mapped: number };
}

// What each mappable OMOP field holds, in plain words
const FIELD_HELP: Record<TableRole, Record<string, string>> = {
  note: {
    note_id:
      "The column that identifies each note. NLP tables link their terms to notes by it.",
    note_text: "The text of the note.",
    note_title: "The title of the note.",
    note_source_value: "The note's identifier or type in the source data.",
    note_class_concept_id: "The kind of note, e.g. a discharge summary.",
    encoding_concept_id: "The text's character encoding, e.g. UTF-8.",
    language_concept_id: "The language the note is written in.",
    note_event_id: "The record of the event the note is about (CDM v5.4).",
    note_event_field_concept_id:
      "The field that note_event_id refers to (CDM v5.4).",
  },
  note_nlp: {
    note_id:
      "The column holding the key of the note each term was found in (the note table's note_id column).",
    lexical_variant: "The term as it appears in the note.",
    snippet: "The text around the term.",
    offset: "Where the term starts in the note.",
    nlp_system: "The NLP system and version that found the term.",
    section_concept_id: "The section of the note the term was found in.",
    term_exists: "Whether the term is asserted (not negated, hypothetical…).",
    term_temporal: "When the term applies, e.g. past or present.",
    term_modifiers: "Other modifiers the NLP system found for the term.",
  },
  standard: {},
  death: {},
};

function initialRows(
  specs: TableFieldSpec[],
  mappings: TableFieldMapping[],
): Record<string, Row> {
  const rows: Record<string, Row> = {};
  for (const spec of specs) {
    const mapping = mappings.find((m) => m.omop_field === spec.omop_field);
    const defaultMode: Mode = spec.required
      ? spec.source
        ? "source"
        : "constant"
      : "none";
    rows[spec.omop_field] = {
      mode: mapping
        ? mapping.map_values
          ? "values"
          : mapping.source_field !== null
            ? "source"
            : "constant"
        : defaultMode,
      sourceField: mapping?.source_field?.toString() ?? "",
      constant: mapping?.constant_value ?? "",
      conceptName: mapping?.concept_name ?? null,
      saved:
        mapping?.map_values && mapping.source_field !== null
          ? {
              sourceField: mapping.source_field.toString(),
              total: mapping.values_total ?? 0,
              mapped: mapping.values_mapped ?? 0,
            }
          : undefined,
    };
  }
  return rows;
}

export function TableFieldMappingsForm({
  scanReportId,
  tableId,
  role,
  fieldMappings,
  scanReportFields,
  canUpdate,
}: {
  scanReportId: number;
  tableId: number;
  role: TableRole;
  fieldMappings: TableFieldMappings;
  scanReportFields: ScanReportField[];
  canUpdate: boolean;
}) {
  const specs = fieldMappings.fields;
  const [rows, setRows] = useState(() =>
    initialRows(specs, fieldMappings.mappings),
  );
  const [saving, setSaving] = useState(false);

  const update = (field: string, change: Partial<Row>) =>
    setRows((current) => ({
      ...current,
      [field]: { ...current[field], ...change },
    }));

  const save = async () => {
    const missing = specs
      .filter((spec) => spec.required)
      .filter((spec) => {
        const row = rows[spec.omop_field];
        return row.mode === "source" || row.mode === "values"
          ? !row.sourceField
          : !row.constant;
      })
      .map((spec) => spec.omop_field);
    if (missing.length) {
      toast.error(`Fill in the required fields: ${missing.join(", ")}`);
      return;
    }

    const mappings: TableFieldMappingInput[] = [];
    for (const spec of specs) {
      const row = rows[spec.omop_field];
      if (row.mode === "values") {
        if (!row.sourceField) {
          toast.error(
            `Choose the column whose values give ${spec.omop_field}, or pick another option.`,
          );
          return;
        }
        mappings.push({
          omop_field: spec.omop_field,
          source_field: Number(row.sourceField),
          map_values: true,
        });
      } else if (row.mode === "source" && row.sourceField) {
        mappings.push({
          omop_field: spec.omop_field,
          source_field: Number(row.sourceField),
        });
      } else if (row.mode === "constant" && row.constant) {
        mappings.push({
          omop_field: spec.omop_field,
          constant_value: row.constant,
        });
      }
    }

    setSaving(true);
    const result = await updateTableFieldMappings(
      scanReportId,
      tableId,
      mappings,
    );
    setSaving(false);
    if (result.errorMessage || !result.data) {
      toast.error(`Saving the field mappings failed. ${result.errorMessage}`);
    } else {
      setRows(initialRows(result.data.fields, result.data.mappings));
      toast.success("Field mappings saved");
    }
  };

  return (
    <Card className="max-w-4xl">
      <CardHeader>
        <CardTitle className="text-xl">
          {role === "note" ? "Note fields" : "Note NLP fields"}
        </CardTitle>
        <CardDescription>
          {role === "note"
            ? "Each row of this table becomes a note. Choose the column or fixed value for each note field."
            : "Each term found by NLP becomes a note_nlp record, alongside the concepts mapped to it. Choose the column or fixed value for the other note_nlp fields."}{" "}
          For concept fields that vary from row to row, such as the kind of
          note, choose &ldquo;Map column values&rdquo; and map the column&apos;s
          values to concepts, as you would for any other field.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {specs.map((spec) => {
          const row = rows[spec.omop_field];
          const modes: { value: Mode; label: string }[] = [
            ...(spec.source
              ? [{ value: "source" as Mode, label: "From a column" }]
              : []),
            ...(spec.values
              ? [{ value: "values" as Mode, label: "Map column values" }]
              : []),
            ...(spec.constant
              ? [
                  {
                    value: "constant" as Mode,
                    label: spec.concept ? "Fixed concept" : "Fixed value",
                  },
                ]
              : []),
            ...(!spec.required
              ? [{ value: "none" as Mode, label: "Not mapped" }]
              : []),
          ];
          return (
            <div
              key={spec.omop_field}
              className="grid gap-2 border-b border-border pb-4 last:border-b-0 md:grid-cols-[16rem_12rem_1fr] md:items-start"
            >
              <div className="flex flex-col gap-1">
                <div className="flex flex-wrap items-center gap-2">
                  <code className="text-sm font-semibold">
                    {spec.omop_field}
                  </code>
                  {spec.required && <Badge variant="secondary">Required</Badge>}
                </div>
                <p className="text-sm text-muted-foreground">
                  {FIELD_HELP[role]?.[spec.omop_field]}
                </p>
              </div>

              {modes.length > 1 ? (
                <Select
                  value={row.mode}
                  onValueChange={(mode) =>
                    update(spec.omop_field, { mode: mode as Mode })
                  }
                  disabled={!canUpdate}
                >
                  <SelectTrigger
                    aria-label={`How ${spec.omop_field} is filled`}
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {modes.map((mode) => (
                      <SelectItem key={mode.value} value={mode.value}>
                        {mode.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <span className="text-sm py-2">{modes[0]?.label}</span>
              )}

              <div>
                {(row.mode === "source" || row.mode === "values") && (
                  <Select
                    value={row.sourceField || undefined}
                    onValueChange={(sourceField) =>
                      update(spec.omop_field, { sourceField })
                    }
                    disabled={!canUpdate}
                  >
                    <SelectTrigger
                      className="max-w-sm"
                      aria-label={`Column for ${spec.omop_field}`}
                    >
                      <SelectValue placeholder="Choose a column" />
                    </SelectTrigger>
                    <SelectContent>
                      {scanReportFields.map((field) => (
                        <SelectItem key={field.id} value={field.id.toString()}>
                          {field.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                {row.mode === "values" && (
                  <ValueMappingStatus
                    row={row}
                    scanReportId={scanReportId}
                    tableId={tableId}
                  />
                )}
                {row.mode === "constant" &&
                  (spec.concept ? (
                    <ConceptIdInput
                      key={`${spec.omop_field}-${row.conceptName}`}
                      ariaLabel={`Concept for ${spec.omop_field}`}
                      value={row.constant}
                      initialName={row.conceptName}
                      onChange={(constant) =>
                        update(spec.omop_field, { constant })
                      }
                      disabled={!canUpdate}
                    />
                  ) : (
                    <Input
                      className="max-w-sm"
                      aria-label={`Value for ${spec.omop_field}`}
                      value={row.constant}
                      maxLength={255}
                      onChange={(event) =>
                        update(spec.omop_field, {
                          constant: event.target.value,
                        })
                      }
                      disabled={!canUpdate}
                    />
                  ))}
              </div>
            </div>
          );
        })}
        <div>
          <Button onClick={save} disabled={!canUpdate || saving}>
            <Save className="h-4 w-4" />
            {saving ? "Saving…" : "Save fields"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// Under a "Map column values" field: what to do next, and how far it's got
function ValueMappingStatus({
  row,
  scanReportId,
  tableId,
}: {
  row: Row;
  scanReportId: number;
  tableId: number;
}) {
  const saved = row.saved && row.saved.sourceField === row.sourceField;
  if (!row.sourceField) {
    return (
      <p className="mt-2 text-sm text-muted-foreground">
        Choose the column whose values say what this field should be, e.g. the
        note type.
      </p>
    );
  }
  if (!saved) {
    return (
      <p className="mt-2 text-sm text-muted-foreground">
        Save, then map each value of this column to a concept.
      </p>
    );
  }
  const { total, mapped } = row.saved!;
  return (
    <div className="mt-2 flex flex-wrap items-center gap-3">
      <span className="text-sm">
        {mapped} of {total} value{total === 1 ? "" : "s"} mapped to concepts
      </span>
      <Button asChild variant="outline" size="sm">
        <Link
          href={`/scanreports/${scanReportId}/tables/${tableId}/fields/${row.sourceField}`}
        >
          Map values
          <ArrowRight className="h-4 w-4" />
        </Link>
      </Button>
      <p className="w-full text-sm text-muted-foreground">
        Each record gets the concept its value is mapped to. Values without a
        concept give 0 (no matching concept).
      </p>
    </div>
  );
}

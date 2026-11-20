"use client";

import { useState } from "react";
import { Plus, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { updateTableNlpSettings } from "@/api/scanreports";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ConceptIdInput } from "./ConceptIdInput";

type LinkField =
  | "source_domain_concept"
  | "relationship_concept"
  | "reverse_relationship_concept";

const LINK_FIELDS: { name: LinkField; label: string; help: string }[] = [
  {
    name: "source_domain_concept",
    label: "note_nlp domain",
    help: "The domain concept that identifies note_nlp records in fact_relationship.",
  },
  {
    name: "relationship_concept",
    label: "note_nlp → derived record",
    help: "The relationship from a note_nlp record to a record derived from it.",
  },
  {
    name: "reverse_relationship_concept",
    label: "Derived record → note_nlp",
    help: "The relationship back from a derived record to its note_nlp record.",
  },
];

interface ExclusionRow {
  key: number;
  sourceField: string;
  values: string; // comma separated, as typed
}

function toRows(settings: NlpSettings): ExclusionRow[] {
  return settings.exclusions.map((exclusion, index) => ({
    key: index,
    sourceField: exclusion.source_field.toString(),
    values: exclusion.excluded_values.join(", "),
  }));
}

function toLinks(settings: NlpSettings): Record<LinkField, string> {
  return {
    source_domain_concept:
      settings.source_domain_concept?.concept_id.toString() ?? "",
    relationship_concept:
      settings.relationship_concept?.concept_id.toString() ?? "",
    reverse_relationship_concept:
      settings.reverse_relationship_concept?.concept_id.toString() ?? "",
  };
}

export function NlpSettingsForm({
  scanReportId,
  tableId,
  settings,
  scanReportFields,
  canUpdate,
}: {
  scanReportId: number;
  tableId: number;
  settings: NlpSettings;
  scanReportFields: ScanReportField[];
  canUpdate: boolean;
}) {
  const [saved, setSaved] = useState(settings);
  const [links, setLinks] = useState(() => toLinks(settings));
  const [exclusions, setExclusions] = useState(() => toRows(settings));
  const [nextKey, setNextKey] = useState(settings.exclusions.length);
  const [saving, setSaving] = useState(false);

  const linkCount = Object.values(links).filter(Boolean).length;

  const save = async () => {
    if (linkCount > 0 && linkCount < LINK_FIELDS.length) {
      toast.error(
        "Set all three fact_relationship concepts, or clear them all to leave derived records unlinked.",
      );
      return;
    }
    const filled = exclusions.filter((row) => row.sourceField || row.values);
    const incomplete = filled.find(
      (row) => !row.sourceField || !row.values.trim(),
    );
    if (incomplete) {
      toast.error("Each exclusion needs a column and at least one value.");
      return;
    }

    setSaving(true);
    const result = await updateTableNlpSettings(scanReportId, tableId, {
      source_domain_concept: links.source_domain_concept
        ? Number(links.source_domain_concept)
        : null,
      relationship_concept: links.relationship_concept
        ? Number(links.relationship_concept)
        : null,
      reverse_relationship_concept: links.reverse_relationship_concept
        ? Number(links.reverse_relationship_concept)
        : null,
      exclusions: filled.map((row) => ({
        source_field: Number(row.sourceField),
        excluded_values: row.values
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
      })),
    });
    setSaving(false);
    if (result.errorMessage || !result.data) {
      toast.error(`Saving the NLP settings failed. ${result.errorMessage}`);
    } else {
      setSaved(result.data);
      setLinks(toLinks(result.data));
      setExclusions(toRows(result.data));
      setNextKey(result.data.exclusions.length);
      toast.success("NLP settings saved");
    }
  };

  return (
    <Card className="max-w-4xl">
      <CardHeader>
        <CardTitle className="text-xl">NLP-derived records</CardTitle>
        <CardDescription>
          Concepts mapped on this table also become records in their own
          domain&apos;s table, such as conditions, with the type concept set
          above (use 32858, NLP, to mark them as NLP-derived). A derived record
          is only written when its note_nlp record is (so when its note was
          found) and the row matches none of the exclusions below. These
          settings only affect the exported rules, so saving doesn&apos;t re-run
          auto-mapping.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-8">
        <section className="flex flex-col gap-3">
          <div>
            <h4 className="font-semibold">Exclusions</h4>
            <p className="text-sm text-muted-foreground">
              Rows whose column holds one of the values (ignoring case) keep
              their note_nlp record but give no derived records, e.g. negated or
              family-history terms. Separate values with commas.
            </p>
          </div>
          {exclusions.map((row) => (
            <div
              key={row.key}
              className="grid gap-2 md:grid-cols-[16rem_1fr_auto] md:items-center"
            >
              <Select
                value={row.sourceField || undefined}
                onValueChange={(sourceField) =>
                  setExclusions((rows) =>
                    rows.map((r) =>
                      r.key === row.key ? { ...r, sourceField } : r,
                    ),
                  )
                }
                disabled={!canUpdate}
              >
                <SelectTrigger aria-label="Exclusion column">
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
              <Input
                aria-label="Excluded values"
                placeholder="e.g. true, 1, yes"
                value={row.values}
                onChange={(event) =>
                  setExclusions((rows) =>
                    rows.map((r) =>
                      r.key === row.key
                        ? { ...r, values: event.target.value }
                        : r,
                    ),
                  )
                }
                disabled={!canUpdate}
              />
              <Button
                variant="ghost"
                size="icon"
                aria-label="Remove exclusion"
                onClick={() =>
                  setExclusions((rows) => rows.filter((r) => r.key !== row.key))
                }
                disabled={!canUpdate}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
          <div>
            <Button
              variant="outline"
              onClick={() => {
                setExclusions((rows) => [
                  ...rows,
                  { key: nextKey, sourceField: "", values: "" },
                ]);
                setNextKey((key) => key + 1);
              }}
              disabled={!canUpdate}
            >
              <Plus className="h-4 w-4" />
              Add exclusion
            </Button>
          </div>
        </section>

        <section className="flex flex-col gap-3">
          <div>
            <h4 className="font-semibold">Link to note_nlp</h4>
            <p className="text-sm text-muted-foreground">
              Each derived record is linked to the note_nlp record it came from
              in fact_relationship, in both directions. The derived
              records&apos; domains come from the vocabulary. Leave these empty
              to write derived records without links.
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              The standard vocabularies don&apos;t yet have a domain concept for
              note_nlp or relationship concepts for NLP derivation, so most
              people should leave these empty. Derived records are still marked
              as NLP-derived by the type concept set above (32858, NLP). Only
              fill these in if your vocabulary has suitable concepts.
            </p>
          </div>
          {LINK_FIELDS.map((field) => (
            <div
              key={field.name}
              className="grid gap-2 md:grid-cols-[16rem_1fr] md:items-start"
            >
              <div>
                <Label htmlFor={field.name}>{field.label}</Label>
                <p className="text-sm text-muted-foreground">{field.help}</p>
              </div>
              <ConceptIdInput
                key={`${field.name}-${saved[field.name]?.concept_id ?? ""}`}
                id={field.name}
                value={links[field.name]}
                initialName={saved[field.name]?.concept_name}
                onChange={(value) =>
                  setLinks((current) => ({ ...current, [field.name]: value }))
                }
                disabled={!canUpdate}
              />
            </div>
          ))}
        </section>

        <div>
          <Button onClick={save} disabled={!canUpdate || saving}>
            <Save className="h-4 w-4" />
            {saving ? "Saving…" : "Save NLP settings"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

"use client";

import { InfoItem } from "@/components/core/InfoItem";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

const CONCEPT_SEARCH_DETAIL_FIELDS: {
  label: string;
  key: keyof ConceptSearchResult;
}[] = [
  { label: "Concept ID", key: "concept_id" },
  { label: "Concept Code", key: "concept_code" },
  { label: "Domain", key: "domain_id" },
  { label: "Vocabulary", key: "vocabulary_id" },
  { label: "Concept Class", key: "concept_class_id" },
];

interface ConceptSearchDetailsSheetProps {
  concept: ConceptSearchResult;
  children: React.ReactNode;
}

export function ConceptSearchDetailsSheet({
  concept,
  children,
}: ConceptSearchDetailsSheetProps) {
  return (
    <Sheet>
      <SheetTrigger asChild>{children}</SheetTrigger>
      <SheetContent className="flex flex-col h-full">
        <SheetHeader className="flex-shrink-0">
          <SheetTitle>
            {concept.concept_id} - {concept.concept_name}
          </SheetTitle>
        </SheetHeader>
        <div className="space-y-3 text-sm flex-1 overflow-y-auto px-1">
          {concept.standard_concept === "S" && (
            <Badge variant="secondary">Standard concept</Badge>
          )}
          {CONCEPT_SEARCH_DETAIL_FIELDS.map((field) => (
            <div key={field.key}>
              <InfoItem label={field.label} value={concept[field.key] ?? ""} />
            </div>
          ))}
          <Button variant="outline" size="sm" className="w-full" asChild>
            <a
              href={`https://athena.ohdsi.org/search-terms/terms/${concept.concept_id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              View on Athena
            </a>
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

"use client";

import { useRef, useState } from "react";
import { lookupConcept } from "@/api/concepts";
import { Input } from "@/components/ui/input";

// A concept id input that shows the concept's name once an id is entered,
// so people can check they typed the concept they meant. Give it a label
// (`id` for a <Label htmlFor>, or `ariaLabel`) naming the field it fills.
export function ConceptIdInput({
  id,
  ariaLabel,
  value,
  onChange,
  initialName,
  disabled,
  placeholder = "Concept ID",
}: {
  id?: string;
  ariaLabel?: string;
  value: string;
  onChange: (value: string) => void;
  initialName?: string | null;
  disabled?: boolean;
  placeholder?: string;
}) {
  const [name, setName] = useState<string | null>(initialName ?? null);
  const [status, setStatus] = useState<"idle" | "loading" | "unknown">("idle");
  // Each lookup's number: a reply is only shown if no edit or newer lookup
  // came after it, so a slow reply can't name a different id than the one shown
  const latest = useRef(0);

  const check = async (text: string) => {
    const request = ++latest.current;
    if (!/^\d+$/.test(text)) {
      setName(null);
      setStatus(text ? "unknown" : "idle");
      return;
    }
    setStatus("loading");
    const concept = await lookupConcept(Number(text));
    if (request !== latest.current) {
      return;
    }
    setName(concept?.concept_name ?? null);
    setStatus(concept ? "idle" : "unknown");
  };

  return (
    <div className="flex flex-col gap-1">
      <Input
        id={id}
        aria-label={ariaLabel}
        inputMode="numeric"
        className="max-w-48"
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        onChange={(event) => {
          latest.current++;
          setName(null);
          setStatus("idle");
          onChange(event.target.value.trim());
        }}
        onBlur={(event) => check(event.target.value.trim())}
      />
      <span className="text-sm text-muted-foreground min-h-5">
        {status === "loading" && "Looking up concept…"}
        {status === "unknown" && "No concept with this ID"}
        {status === "idle" && name}
      </span>
    </div>
  );
}

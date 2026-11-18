/*
 * Browser-side filtering, sorting and paging over the mock data.
 * Demonstration only: in the integration PR the Registry API does this.
 */
import type { Mapping, MappingSet, SearchField, Sort } from "../../types/mapping-registry";

function mappingValue(mapping: Mapping, field: SearchField): string {
  switch (field) {
    case "sourceTerm": return mapping.sourceTerm;
    case "conceptId": return mapping.conceptId;
    case "mappingSet": return mapping.mappingSet;
    case "vocabulary": return mapping.vocabulary;
    case "vocabularyVersion": return mapping.vocabularyVersion;
    case "canonicalIri": return mapping.canonicalIri;
    case "license": return mapping.license;
    case "predicate": return mapping.predicate;
    case "justification": return mapping.justification;
    case "publisher": return mapping.publisher;
    case "mappingSetVersion": return mapping.mappingSetVersion;
  }
}

function mappingSetValue(set: MappingSet, field: SearchField): string {
  switch (field) {
    case "publisher": return set.publisher;
    case "mappingSetVersion": return set.version;
    case "license": return set.license;
    default: return set.title;
  }
}

export function editDistance(left: string, right: string): number {
  const previous = Array.from({ length: right.length + 1 }, (_, i) => i);
  for (let i = 1; i <= left.length; i++) {
    let diagonal = previous[0];
    previous[0] = i;
    for (let j = 1; j <= right.length; j++) {
      const upper = previous[j];
      previous[j] = Math.min(
        previous[j] + 1,
        previous[j - 1] + 1,
        diagonal + (left[i - 1] === right[j - 1] ? 0 : 1),
      );
      diagonal = upper;
    }
  }
  return previous[right.length];
}

// Substring match on the chosen field, plus a small typo tolerance for source terms.
export function matchesMapping(mapping: Mapping, field: SearchField, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  const haystack = mappingValue(mapping, field).toLowerCase();
  if (haystack.includes(needle)) return true;
  if (field !== "sourceTerm" || needle.length < 4) return false;
  return haystack.split(/\W+/).some((word) => editDistance(word, needle) <= 2);
}

export function matchesMappingSet(set: MappingSet, field: SearchField, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return mappingSetValue(set, field).toLowerCase().includes(needle);
}

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

export function sortRecords<T>(records: T[], sort: Sort): T[] {
  if (!sort) return records;
  return [...records].sort((a, b) => {
    const left = String((a as Record<string, unknown>)[sort.key] ?? "");
    const right = String((b as Record<string, unknown>)[sort.key] ?? "");
    const result = collator.compare(left, right);
    return sort.direction === "asc" ? result : -result;
  });
}

export function paginate<T>(records: T[], page: number, pageSize: number): T[] {
  return records.slice((page - 1) * pageSize, page * pageSize);
}

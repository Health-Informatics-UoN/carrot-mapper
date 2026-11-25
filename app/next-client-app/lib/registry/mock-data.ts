/*
 * Demo data for the UI PR only. Nothing outside hooks/useRegistrySearch.ts may
 * import from this file, so the integration PR can delete it without touching
 * any component.
 */
import type { Mapping, MappingSet, RegistryStats } from "../../types/mapping-registry";

export const MOCK_MAPPINGS: Mapping[] = [
  {
    id: "map-001", mappingSetId: "set-001", sourceTerm: "Diabetes", subjectId: "SITE_A:DM01",
    canonicalIri: "https://example.org/terms/diabetes", targetConcept: "Diabetes mellitus",
    conceptId: "201820", vocabulary: "SNOMED", vocabularyVersion: "2025-09",
    publisher: "Researcher A", mappingSet: "Clinical terminology mappings",
    mappingSetVersion: "1.0.0", predicate: "skos:exactMatch",
    justification: "semapv:ManualMappingCuration", license: "CC-BY-4.0", publishedAt: "2026-10-11",
  },
  {
    id: "map-002", mappingSetId: "set-002", sourceTerm: "Diabetes", subjectId: "SITE_B:DM02",
    canonicalIri: "https://example.org/terms/diabetes", targetConcept: "Type 2 diabetes mellitus",
    conceptId: "201826", vocabulary: "SNOMED", vocabularyVersion: "2025-09",
    publisher: "Researcher B", mappingSet: "Metabolic conditions",
    mappingSetVersion: "2.1.0", predicate: "skos:closeMatch",
    justification: "semapv:ManualMappingCuration", license: "CC0-1.0", publishedAt: "2026-10-19",
  },
  {
    id: "map-003", mappingSetId: "set-003", sourceTerm: "Diabetes", subjectId: "SITE_C:DM03",
    canonicalIri: "https://example.org/terms/diabetes", targetConcept: "Diabetes mellitus",
    conceptId: "201820", vocabulary: "SNOMED", vocabularyVersion: "2025-09",
    publisher: "Researcher C", mappingSet: "Community OMOP mappings",
    mappingSetVersion: "1.2.0", predicate: "skos:exactMatch",
    justification: "semapv:LexicalMatching", license: "ODbL-1.0", publishedAt: "2026-11-02",
  },
  {
    id: "map-004", mappingSetId: "set-004", sourceTerm: "Diabetes", subjectId: "SITE_D:DM04",
    canonicalIri: "https://example.org/terms/diabetes", targetConcept: "Diabetes mellitus type 1",
    conceptId: "201254", vocabulary: "SNOMED", vocabularyVersion: "2025-09",
    publisher: "Researcher D", mappingSet: "Endocrinology source terms",
    mappingSetVersion: "0.9.0", predicate: "skos:relatedMatch",
    justification: "semapv:ManualMappingCuration", license: "CC-BY-4.0", publishedAt: "2026-11-08",
  },
  {
    id: "map-005", mappingSetId: "set-001", sourceTerm: "Hypertension", subjectId: "SITE_A:HT01",
    canonicalIri: "https://example.org/terms/hypertension", targetConcept: "Hypertensive disorder",
    conceptId: "316866", vocabulary: "SNOMED", vocabularyVersion: "2025-09",
    publisher: "Researcher A", mappingSet: "Clinical terminology mappings",
    mappingSetVersion: "1.0.0", predicate: "skos:exactMatch",
    justification: "semapv:ManualMappingCuration", license: "CC-BY-4.0", publishedAt: "2026-10-11",
  },
  {
    id: "map-006", mappingSetId: "set-005", sourceTerm: "Hypertension", subjectId: "SITE_E:HT02",
    canonicalIri: "https://example.org/terms/hypertension", targetConcept: "Essential hypertension",
    conceptId: "320128", vocabulary: "SNOMED", vocabularyVersion: "2025-09",
    publisher: "Researcher E", mappingSet: "Cardiovascular mappings",
    mappingSetVersion: "1.1.0", predicate: "skos:closeMatch",
    justification: "semapv:ManualMappingCuration", license: "CC0-1.0", publishedAt: "2026-11-10",
  },
  {
    id: "map-007", mappingSetId: "set-003", sourceTerm: "Asthma", subjectId: "SITE_C:AS01",
    canonicalIri: "https://example.org/terms/asthma", targetConcept: "Asthma",
    conceptId: "317009", vocabulary: "SNOMED", vocabularyVersion: "2025-09",
    publisher: "Researcher C", mappingSet: "Community OMOP mappings",
    mappingSetVersion: "1.2.0", predicate: "skos:exactMatch",
    justification: "semapv:LexicalMatching", license: "ODbL-1.0", publishedAt: "2026-11-02",
  },
  {
    id: "map-008", mappingSetId: "set-006", sourceTerm: "Asthma", subjectId: "SITE_F:AS02",
    canonicalIri: "https://example.org/terms/asthma", targetConcept: "Asthma",
    conceptId: "317009", vocabulary: "SNOMED", vocabularyVersion: "2025-09",
    publisher: "Researcher F", mappingSet: "Respiratory cohort mappings",
    mappingSetVersion: "1.0.0", predicate: "skos:exactMatch",
    justification: "semapv:ManualMappingCuration", license: "CC0-1.0", publishedAt: "2026-11-14",
  },
  {
    id: "map-009", mappingSetId: "set-001", sourceTerm: "Chronic kidney disease", subjectId: "SITE_A:CKD01",
    canonicalIri: "https://example.org/terms/ckd", targetConcept: "Chronic kidney disease",
    conceptId: "46271022", vocabulary: "SNOMED", vocabularyVersion: "2025-09",
    publisher: "Researcher A", mappingSet: "Clinical terminology mappings",
    mappingSetVersion: "1.0.0", predicate: "skos:exactMatch",
    justification: "semapv:ManualMappingCuration", license: "CC-BY-4.0", publishedAt: "2026-10-11",
  },
  {
    id: "map-010", mappingSetId: "set-007", sourceTerm: "Chronic kidney disease", subjectId: "SITE_G:CKD02",
    canonicalIri: "https://example.org/terms/ckd", targetConcept: "Chronic kidney disease stage 3",
    conceptId: "443611", vocabulary: "SNOMED", vocabularyVersion: "2025-09",
    publisher: "Researcher G", mappingSet: "Renal registry mappings",
    mappingSetVersion: "2.0.0", predicate: "skos:relatedMatch",
    justification: "semapv:ManualMappingCuration", license: "CC-BY-4.0", publishedAt: "2026-11-15",
  },
  {
    id: "map-011", mappingSetId: "set-003", sourceTerm: "Headache", subjectId: "SITE_C:HD01",
    canonicalIri: "https://example.org/terms/headache", targetConcept: "Headache",
    conceptId: "378253", vocabulary: "SNOMED", vocabularyVersion: "2025-09",
    publisher: "Researcher C", mappingSet: "Community OMOP mappings",
    mappingSetVersion: "1.2.0", predicate: "skos:exactMatch",
    justification: "semapv:LexicalMatching", license: "ODbL-1.0", publishedAt: "2026-11-02",
  },
];

export const MOCK_DESCRIPTIONS: Record<string, string> = {
  "Clinical terminology mappings": "Reusable terminology mappings for clinical source data.",
  "Metabolic conditions": "Mappings for source terms describing metabolic disorders.",
  "Community OMOP mappings": "Community-contributed mappings to OMOP vocabulary concepts.",
  "Endocrinology source terms": "Endocrinology source term mapping examples.",
  "Cardiovascular mappings": "Terminology mappings for cardiovascular source datasets.",
  "Respiratory cohort mappings": "Mappings for respiratory data standardisation.",
  "Renal registry mappings": "Published mappings for renal and kidney-related data.",
};

// Mapping sets are grouped from the mock mappings by title + version + publisher.
export const MOCK_MAPPING_SETS: MappingSet[] = (() => {
  const sets = new Map<string, MappingSet>();
  let setNumber = 0;
  MOCK_MAPPINGS.forEach((mapping) => {
    const key = `${mapping.mappingSet}::${mapping.mappingSetVersion}::${mapping.publisher}`;
    let set = sets.get(key);
    if (!set) {
      setNumber += 1;
      set = {
        id: `set-${String(setNumber).padStart(3, "0")}`,
        title: mapping.mappingSet,
        version: mapping.mappingSetVersion,
        publisher: mapping.publisher,
        license: mapping.license,
        publishedAt: mapping.publishedAt,
        description: MOCK_DESCRIPTIONS[mapping.mappingSet] ?? "Published source-to-OMOP mappings.",
        mappings: [],
      };
      sets.set(key, set);
    }
    set.mappings.push(mapping);
  });
  return Array.from(sets.values());
})();

// Explicitly demo data: these numbers must never be shown as live Registry stats.
export const MOCK_STATS: RegistryStats = {
  totalMappings: MOCK_MAPPINGS.length,
  totalSets: MOCK_MAPPING_SETS.length,
};

export function getMappingById(id: string): Mapping | null {
  return MOCK_MAPPINGS.find((mapping) => mapping.id === id) ?? null;
}

export function getMappingSetById(id: string): MappingSet | null {
  return MOCK_MAPPING_SETS.find((mappingSet) => mappingSet.id === id) ?? null;
}

export function getAlternativeMappings(mapping: Mapping): Mapping[] {
  const sourceTerm = mapping.sourceTerm.toLowerCase();
  return MOCK_MAPPINGS.filter(
    (candidate) =>
      candidate.id !== mapping.id &&
      candidate.sourceTerm.toLowerCase() === sourceTerm,
  );
}

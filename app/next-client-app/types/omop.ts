interface Concept {
  concept_id: number;
  concept_name: string;
  concept_code: string;
  // TODO: these are added in code, not returned in API.
  scan_report_concept_id?: number;
  creation_type: string;
}

interface ConceptDetail extends Concept {
  domain_id: string;
  vocabulary_id: string;
  concept_class_id: string;
  standard_concept: string;
  valid_start_date: string;
  valid_end_date: string;
  invalid_reason: string;
}
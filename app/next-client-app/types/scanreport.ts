interface ScanReport {
  id: number;
  dataset: string;
  description: string | null;
  parent_dataset: DatasetStrict;
  data_partner: string;
  mapping_status: {
    value: string;
  };
  upload_status?: {
    value: string;
  };
  upload_status_details: string;
  created_at: Date;
  hidden: boolean;
  visibility: string;
  author: User;
  viewers: User[];
  editors: User[];
}

interface ScanReportTable {
  id: number;
  created_at: Date;
  updated_at: Date;
  name: string;
  scan_report: number;
  person_id: ScanReportField | null;
  date_event: ScanReportField | null;
  permissions: Permission[];
  jobs: Job[];
  trigger_reuse: boolean;
  table_role: TableRole;
  type_concept: number | null;
}

type TableRole = "standard" | "death" | "note" | "note_nlp";

interface ConceptSummary {
  concept_id: number;
  concept_name: string | null;
}

// An OMOP field a note / note_nlp table can map at table level
interface TableFieldSpec {
  omop_field: string;
  required: boolean;
  source: boolean; // can take a source field
  constant: boolean; // can take a constant value
  concept: boolean; // the constant must be a concept id
  values: boolean; // can take the concepts mapped to a column's values
}

interface TableFieldMapping {
  omop_field: string;
  source_field: number | null;
  constant_value: string | null;
  concept_name: string | null;
  map_values: boolean;
  // With map_values: how many of the column's values have a concept
  source_field_name?: string;
  values_total?: number;
  values_mapped?: number;
}

interface TableFieldMappings {
  fields: TableFieldSpec[];
  mappings: TableFieldMapping[];
}

type TableFieldMappingInput =
  | { omop_field: string; source_field: number }
  | { omop_field: string; constant_value: string }
  | { omop_field: string; source_field: number; map_values: true };

interface NlpExclusion {
  source_field: number;
  source_field_name: string;
  excluded_values: string[];
}

interface NlpSettings {
  source_domain_concept: ConceptSummary | null;
  relationship_concept: ConceptSummary | null;
  reverse_relationship_concept: ConceptSummary | null;
  exclusions: NlpExclusion[];
}

interface NlpSettingsInput {
  source_domain_concept: number | null;
  relationship_concept: number | null;
  reverse_relationship_concept: number | null;
  exclusions: { source_field: number; excluded_values: string[] }[];
}

interface ScanReportField {
  id: number;
  created_at: Date;
  updated_at: Date;
  name: string;
  description_column: string;
  type_column: string;
  max_length: number;
  nrows: number;
  nrows_checked: number;
  fraction_empty: string;
  nunique_values: number;
  fraction_unique: string;
  ignore_column: boolean | null;
  is_patient_id: boolean;
  is_ignore: boolean;
  classification_system: string | null;
  pass_from_source: boolean;
  concept_id: number;
  concepts?: Concept[];
  permissions: Permission[];
  field_description: string | null;
  scan_report_table: number;
}

interface ScanReportConcept {
  id: number;
  object_id: number;
  creation_type: "V" | "M" | "R" | "X";
  concept: Concept | number;
  content_type: number;
}

interface ScanReportConceptV3 {
  id: number;
  object_id: number;
  creation_type: "V" | "M" | "R" | "X";
  concept: Concept;
  content_type: number;
}

interface ScanReportConceptDetailV3 extends ScanReportConceptV3 {
  created_at: Date;
  created_by: User;
  confidence: number;
  description: string;
  mapping_tool: string;
  mapping_tool_version: string;
  concept: ConceptDetail;
}

interface ScanReportValue {
  id: number;
  value: string;
  frequency: number;
  value_description: string;
  scan_report_field: number;
  // TODO: These should be added in a inherited type, as they are not returned from the API.
  concepts?: Concept[];
  permissions: Permission[];
}

interface ScanReportValueV3 {
  id: number;
  value: string;
  frequency: number;
  value_description: string;
  scan_report_field: number;
  concepts: ScanReportConceptV3[];
  mapping_recommendations: MappingRecommendation[];
}

interface ScanReportFieldV3 {
  id: number;
  name: string;
  description_column: string;
  type_column: string;
  concepts: ScanReportConceptV3[];
  mapping_recommendations: MappingRecommendation[];
}

type ConceptTableAction =
  | { type: "add"; rowId: number; concept: ScanReportConceptV3 }
  | { type: "delete"; rowId: number; conceptId: number };

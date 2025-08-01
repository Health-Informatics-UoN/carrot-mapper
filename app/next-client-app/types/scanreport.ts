interface ScanReport {
  id: number;
  dataset: string;
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
  creation_type: "V" | "M" | "R";
  concept: Concept | number;
  content_type: number;
}

interface ScanReportConceptV3 {
  id: number;
  object_id: number;
  creation_type: "V" | "M" | "R";
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
  concept: Concept;
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
}

interface Status {
  value: string;
}

interface ScanReport {
  id: number;
  dataset: string;
  parent_dataset: DatasetStrict;
  data_partner: string;
  mapping_status: Status;
  upload_status: Status;
  created_at: Date;
  hidden: boolean;
  visibility: string;
  author: User;
  viewers: number[];
  editors: number[];
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
  death_table: boolean;
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
  creation_type: string;
  concept: Concept | number;
  content_type: number;
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

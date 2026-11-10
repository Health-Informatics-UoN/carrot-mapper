type FileTypeFormat =
  | "application/json"
  | "application/json_v1"
  | "application/json_v2"
  | "image/svg+xml"
  | "text/csv"
  | "text/x-sssom+tsv";
type FileTypeValue =
  | "mapping_json"
  | "mapping_json_v2"
  | "mapping_csv"
  | "mapping_sssom"
  | "mapping_svg"
  | "data_dictionary"
  | "scan_report";
interface FileType {
  value: FileTypeValue;
  display_name:
    | "Mapping Rules JSON"
    | "Mapping Rules JSON V2"
    | "Mapping Rules CSV"
    | "Mapping Rules SSSOM"
    | "Mapping Rules SVG"
    | "Data Dictionary"
    | "Scan Report";
}

interface FileDownload {
  id: number;
  scan_report: number;
  name: string;
  created_at: Date;
  user: User;
  file_type: FileType;
  file_url: string;
}

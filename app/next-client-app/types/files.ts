import { User } from "./dataset";

export type FileTypeFormat = "application/json" | "image/svg+xml" | "text/csv";
export type FileTypeFormatWithVersion = "application/json_v1" | "application/json_v2" | "image/svg+xml" | "text/csv";
export type FileTypeValue =
  | "mapping_json"
  | "mapping_csv"
  | "mapping_svg"
  | "data_dictionary"
  | "scan_report";

export interface FileType {
  value: FileTypeValue;
  display_name:
    | "Mapping Rules JSON"
    | "Mapping Rules CSV"
    | "Mapping Rules SVG"
    | "Data Dictionary"
    | "Scan Report";
}

export interface FileDownload {
  id: number;
  scan_report: number;
  name: string;
  created_at: Date;
  user: User;
  file_type: FileType;
  file_url: string;
}

/**
 * Interface for list view parameters.
 */
interface FilterParameters {
  hidden?: boolean;
  page_size?: number;
  p?: number;
  ordering?: string;
}

interface FilterOption {
  label: string;
  value: string;
  icon?: string;
  color?: string;
}

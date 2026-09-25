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

/**
 * URL search params for the vocabularies page's "Search Concepts" tab.
 * Namespaced (search_p/search_page_size) to avoid colliding with the
 * "Vocabularies" tab's own FilterParameters on the same page/URL.
 */
interface ConceptSearchParameters {
  tab?: string;
  q?: string;
  vocabulary_id?: string;
  domain_id?: string;
  concept_class_id?: string;
  standard_concept?: string;
  search_p?: number;
  search_page_size?: number;
}

export interface UnisonConceptItem {
  accuracy: number;
  conceptId: number;
  conceptName: string;
  conceptCode: string;
  vocabulary: string;
  domain: string;
  conceptClass: string;
  explanation: string;
}

export interface UnisonConceptResponse {
  items: UnisonConceptItem[];
  count: number;
}

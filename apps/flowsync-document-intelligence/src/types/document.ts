export type DocumentStatus =
  | "received"
  | "ingested"
  | "classified"
  | "parsed"
  | "extracted"
  | "transformed"
  | "validated"
  | "matched"
  | "review_required"
  | "approved"
  | "export_ready"
  | "exported"
  | "failed";

export type DocumentType = "invoice" | "purchase_order" | "receipt";

export interface DocumentSummary {
  document_id: string;
  filename: string;
  document_type: DocumentType;
  status: DocumentStatus;
  confidence: number;
  current_stage: string;
  received_at: string;
}

export interface ProcessingStatus {
  stage: string;
  status: string;
  occurred_at: string;
}

export interface ValidationIssue {
  issue_id: string;
  severity: "warning" | "error";
  field: string;
  rule_id: string;
  code: string;
  message: string;
}

export interface MatchingResult {
  match_id: string;
  entity_type: string;
  candidate_id: string;
  confidence: number;
  status: string;
}

export interface DocumentListQuery {
  status?: DocumentStatus;
  document_type?: DocumentType;
  limit?: number;
  offset?: number;
}


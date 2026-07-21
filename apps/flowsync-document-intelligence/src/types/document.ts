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
  updated_at?: string;
  source_label?: string;
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

export interface PurchaseOrderLineItem {
  item_code: string | null; barcode: string | null; description: string | null; unit: string | null;
  quantity: string | null; unit_price: string | null; net_amount: string | null;
}

export interface PurchaseOrderFinding {
  severity: "warning" | "error"; code: string; field: string; message: string;
}

export interface PurchaseOrderResult {
  document_type: "purchase_order";
  purchase_order_number: string | null; buyer: string | null; supplier: string | null; ship_to: string | null;
  order_date: string | null; delivery_date: string | null; currency: string | null;
  subtotal: string | null; tax: string | null; total: string | null;
  line_items: PurchaseOrderLineItem[]; terms: string | null;
  source_lineage: { source_type: string; source_name: string; extraction_rule: string; page_count: number | null };
  validation: { status: string; is_valid: boolean; tolerance: string; findings: PurchaseOrderFinding[] };
  extraction_warnings: PurchaseOrderFinding[];
}

function nullableBoundedString(value: unknown, maxLength = 512): value is string | null {
  return value === null || isBoundedString(value, maxLength);
}

export function parsePurchaseOrderResult(value: unknown): PurchaseOrderResult | null {
  if (!isRecord(value) || value.document_type !== "purchase_order" || !Array.isArray(value.line_items) || !isRecord(value.source_lineage) || !isRecord(value.validation) || !Array.isArray(value.validation.findings) || !Array.isArray(value.extraction_warnings)) return null;
  const scalarFields = ["purchase_order_number", "buyer", "supplier", "ship_to", "order_date", "delivery_date", "currency", "subtotal", "tax", "total", "terms"] as const;
  if (scalarFields.some((field) => !nullableBoundedString(value[field]))) return null;
  const lineItems = value.line_items.map((item) => {
    if (!isRecord(item)) return null;
    const fields = ["item_code", "barcode", "description", "unit", "quantity", "unit_price", "net_amount"] as const;
    return fields.every((field) => nullableBoundedString(item[field])) ? item : null;
  });
  const parseFinding = (finding: unknown) => isRecord(finding) && (finding.severity === "warning" || finding.severity === "error") && isBoundedString(finding.code, 64) && isBoundedString(finding.field, 128) && isBoundedString(finding.message, 256) ? finding : null;
  if (lineItems.includes(null) || value.validation.findings.map(parseFinding).includes(null) || value.extraction_warnings.map(parseFinding).includes(null) || !isBoundedString(value.source_lineage.source_type, 64) || !isBoundedString(value.source_lineage.source_name, 128) || !isBoundedString(value.source_lineage.extraction_rule, 128) || !isBoundedString(value.validation.status, 64) || typeof value.validation.is_valid !== "boolean" || !isBoundedString(value.validation.tolerance, 32)) return null;
  return value as unknown as PurchaseOrderResult;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isBoundedString(value: unknown, maxLength = 256): value is string {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    value.length <= maxLength &&
    !/[\u0000-\u001f\u007f]/.test(value)
  );
}

const DOCUMENT_STATUS_VALUES: ReadonlySet<string> = new Set<DocumentStatus>([
  "received", "ingested", "classified", "parsed", "extracted", "transformed",
  "validated", "matched", "review_required", "approved", "export_ready",
  "exported", "failed",
]);

const DOCUMENT_TYPE_VALUES: ReadonlySet<string> = new Set<DocumentType>([
  "invoice", "purchase_order", "receipt",
]);

export function parseDocumentSummary(value: unknown): DocumentSummary | null {
  if (!isRecord(value)) return null;
  if (
    !isBoundedString(value.document_id, 128) ||
    !isBoundedString(value.filename, 256) ||
    !isBoundedString(value.document_type, 64) ||
    !DOCUMENT_TYPE_VALUES.has(value.document_type) ||
    !isBoundedString(value.status, 64) ||
    !DOCUMENT_STATUS_VALUES.has(value.status) ||
    typeof value.confidence !== "number" ||
    !Number.isFinite(value.confidence) ||
    value.confidence < 0 ||
    value.confidence > 1 ||
    !isBoundedString(value.current_stage, 128) ||
    !isBoundedString(value.received_at, 64)
  ) {
    return null;
  }
  if (value.updated_at !== undefined && !isBoundedString(value.updated_at, 64)) return null;
  if (value.source_label !== undefined && !isBoundedString(value.source_label, 128)) return null;

  return {
    document_id: value.document_id,
    filename: value.filename,
    document_type: value.document_type as DocumentType,
    status: value.status as DocumentStatus,
    confidence: value.confidence,
    current_stage: value.current_stage,
    received_at: value.received_at,
    ...(value.updated_at ? { updated_at: value.updated_at } : {}),
    ...(value.source_label ? { source_label: value.source_label } : {}),
  };
}

export function parseProcessingStatus(value: unknown): ProcessingStatus | null {
  if (
    !isRecord(value) ||
    !isBoundedString(value.stage, 128) ||
    !isBoundedString(value.status, 64) ||
    !isBoundedString(value.occurred_at, 64)
  ) {
    return null;
  }
  return { stage: value.stage, status: value.status, occurred_at: value.occurred_at };
}

export function parseValidationIssue(value: unknown): ValidationIssue | null {
  if (
    !isRecord(value) ||
    !isBoundedString(value.issue_id, 128) ||
    (value.severity !== "warning" && value.severity !== "error") ||
    !isBoundedString(value.field, 128) ||
    !isBoundedString(value.rule_id, 128) ||
    !isBoundedString(value.code, 64) ||
    !isBoundedString(value.message, 256)
  ) {
    return null;
  }
  return {
    issue_id: value.issue_id,
    severity: value.severity,
    field: value.field,
    rule_id: value.rule_id,
    code: value.code,
    message: value.message,
  };
}

export function parseMatchingResult(value: unknown): MatchingResult | null {
  if (
    !isRecord(value) ||
    !isBoundedString(value.match_id, 128) ||
    !isBoundedString(value.entity_type, 128) ||
    !isBoundedString(value.candidate_id, 128) ||
    typeof value.confidence !== "number" ||
    !Number.isFinite(value.confidence) ||
    value.confidence < 0 ||
    value.confidence > 1 ||
    !isBoundedString(value.status, 64)
  ) {
    return null;
  }
  return {
    match_id: value.match_id,
    entity_type: value.entity_type,
    candidate_id: value.candidate_id,
    confidence: value.confidence,
    status: value.status,
  };
}

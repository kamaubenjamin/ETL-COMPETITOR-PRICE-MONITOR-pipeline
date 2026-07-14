import type {
  DocumentSummary,
  MatchingResult,
  ProcessingStatus,
  ValidationIssue,
} from "../types/document";
import type {
  DocumentDetailViewModel,
  DocumentRowViewModel,
  DocumentSummaryMetric,
} from "../types/viewModels";

const LABEL_OVERRIDES: Record<string, string> = {
  purchase_order: "Purchase order",
  review_required: "Review required",
  export_ready: "Export ready",
};

export function displayLabel(value: string): string {
  return LABEL_OVERRIDES[value] ?? value.replaceAll("_", " ").replace(/^./, (character) => character.toUpperCase());
}

export function formatDateTime(value: string | undefined): string {
  if (!value) return "Not available";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return "Not available";
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function toDocumentRow(document: DocumentSummary): DocumentRowViewModel {
  const row = {
    id: document.document_id,
    filename: document.filename,
    type: displayLabel(document.document_type),
    status: document.status,
    statusLabel: displayLabel(document.status),
    currentStage: displayLabel(document.current_stage),
    confidence: formatConfidence(document.confidence),
    receivedAt: formatDateTime(document.received_at),
    updatedAt: formatDateTime(document.updated_at),
    source: document.source_label ?? "Not available",
  };
  return {
    ...row,
    searchText: [row.id, row.filename, row.type, row.statusLabel, row.currentStage, row.source]
      .join(" ")
      .toLocaleLowerCase(),
  };
}

export function toDocumentSummaryMetrics(documents: DocumentSummary[]): DocumentSummaryMetric[] {
  const activeStatuses = new Set(["received", "ingested", "classified", "parsed", "extracted", "transformed", "validated", "matched"]);
  const readyStatuses = new Set(["approved", "export_ready", "exported"]);
  return [
    { id: "total", label: "Current results", value: documents.length, detail: "Loaded from the API", tone: "neutral" },
    { id: "active", label: "Active", value: documents.filter((item) => activeStatuses.has(item.status)).length, detail: "In intake or processing", tone: "warning" },
    { id: "review", label: "Review required", value: documents.filter((item) => item.status === "review_required").length, detail: "Awaiting operator review", tone: "critical" },
    { id: "ready", label: "Ready", value: documents.filter((item) => readyStatuses.has(item.status)).length, detail: "Approved or export ready", tone: "positive" },
    { id: "failed", label: "Failed", value: documents.filter((item) => item.status === "failed").length, detail: "Requires investigation", tone: "critical" },
  ];
}

export function toDocumentDetailViewModel(
  document: DocumentSummary,
  processing: ProcessingStatus[],
  validation: ValidationIssue[],
  matching: MatchingResult[],
): DocumentDetailViewModel {
  const highestMatch = matching.reduce<number | null>(
    (highest, item) => highest === null || item.confidence > highest ? item.confidence : highest,
    null,
  );
  return {
    id: document.document_id,
    filename: document.filename,
    type: displayLabel(document.document_type),
    status: document.status,
    statusLabel: displayLabel(document.status),
    currentStage: displayLabel(document.current_stage),
    confidence: formatConfidence(document.confidence),
    receivedAt: formatDateTime(document.received_at),
    updatedAt: formatDateTime(document.updated_at),
    source: document.source_label ?? "Not available",
    processing: processing.map((item) => ({
      stage: displayLabel(item.stage),
      status: displayLabel(item.status),
      occurredAt: formatDateTime(item.occurred_at),
    })),
    validationIssueCount: validation.length,
    validationErrorCount: validation.filter((item) => item.severity === "error").length,
    matchingResultCount: matching.length,
    highestMatchConfidence: highestMatch === null ? "Not available" : formatConfidence(highestMatch),
  };
}


import type { DocumentStatus } from "../types/document";
import { displayLabel } from "../state/documentViewModels";

interface StatusChipProps {
  status: DocumentStatus | string;
  label?: string;
}

const POSITIVE = new Set(["approved", "export_ready", "exported", "succeeded", "matched"]);
const WARNING = new Set(["received", "ingested", "classified", "parsed", "extracted", "transformed", "validated", "running"]);
const CRITICAL = new Set(["review_required", "failed", "error"]);

export function StatusChip({ status, label }: StatusChipProps) {
  const tone = POSITIVE.has(status) ? "positive" : WARNING.has(status) ? "warning" : CRITICAL.has(status) ? "critical" : "neutral";
  return <span className={`status-chip status-chip--${tone}`}>{label ?? displayLabel(status)}</span>;
}


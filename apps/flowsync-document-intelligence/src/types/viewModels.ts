import type { StatusTone } from "../components/StatusCard";
import type { DocumentStatus } from "./document";

export interface DocumentRowViewModel {
  id: string;
  filename: string;
  type: string;
  status: DocumentStatus;
  statusLabel: string;
  currentStage: string;
  confidence: string;
  receivedAt: string;
  updatedAt: string;
  source: string;
  searchText: string;
}

export interface DocumentSummaryMetric {
  id: "total" | "active" | "review" | "ready" | "failed";
  label: string;
  value: number;
  detail: string;
  tone: StatusTone;
}

export interface DocumentDetailViewModel {
  id: string;
  filename: string;
  type: string;
  status: DocumentStatus;
  statusLabel: string;
  currentStage: string;
  confidence: string;
  receivedAt: string;
  updatedAt: string;
  source: string;
  processing: Array<{ stage: string; status: string; occurredAt: string }>;
  validationIssueCount: number;
  validationErrorCount: number;
  matchingResultCount: number;
  highestMatchConfidence: string;
}


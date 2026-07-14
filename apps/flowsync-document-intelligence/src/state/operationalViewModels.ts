import type { AuditEventSummary } from "../types/audit";
import type { MatchingResult, ValidationIssue } from "../types/document";
import type { CorrectionSummary, ReprocessPlanSummary, ReviewCaseSummary } from "../types/review";
import type { WorkflowRunSummary } from "../types/workflow";
import { displayLabel, formatConfidence, formatDateTime } from "./documentViewModels";

export function validationMetrics(issues: ValidationIssue[]) {
  const errors = issues.filter((issue) => issue.severity === "error").length;
  const warnings = issues.length - errors;
  return { total: issues.length, errors, warnings, status: errors ? "Action required" : warnings ? "Warnings" : "Passed" };
}

export function matchingMetrics(results: MatchingResult[]) {
  const highest = results.reduce<MatchingResult | null>((best, item) => !best || item.confidence > best.confidence ? item : best, null);
  return {
    status: highest ? displayLabel(highest.status) : "No match data",
    confidence: highest ? formatConfidence(highest.confidence) : "Not available",
    entity: highest ? highest.candidate_id : "Not available",
    count: results.length,
  };
}

export function reviewMetrics(cases: ReviewCaseSummary[]) {
  return {
    total: cases.length,
    required: cases.filter((item) => item.status === "review_required").length,
    inReview: cases.filter((item) => item.status === "in_review").length,
    closed: cases.filter((item) => ["approved", "rejected", "skipped", "resolved"].includes(item.status)).length,
    highPriority: cases.filter((item) => item.priority === "high" || item.priority === "urgent").length,
  };
}

export function formatDuration(value: number | null): string {
  if (value === null) return "In progress";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(1)} s`;
}

export function correctionTimeline(items: CorrectionSummary[]) {
  return items.map((item) => ({
    id: item.correction_id,
    title: displayLabel(item.operation),
    detail: `${displayLabel(item.field_path)} - ${displayLabel(item.reason_code)} (${displayLabel(item.source_stage)})`,
    timestamp: formatDateTime(item.occurred_at),
  }));
}

export function reprocessTimeline(items: ReprocessPlanSummary[]) {
  return items.map((item) => ({
    id: item.plan_id,
    title: `${displayLabel(item.requested_from_stage)} to ${displayLabel(item.requested_target_stage)}`,
    detail: `${item.invalidated_artifact_count} invalidated, ${item.retained_artifact_count} retained - planning only`,
    timestamp: formatDateTime(item.created_at),
    status: item.mode,
  }));
}

export function workflowTimeline(items: WorkflowRunSummary[]) {
  return items.map((item) => ({
    id: item.run_id,
    title: displayLabel(item.workflow_name),
    detail: `${item.run_id} - ${formatDuration(item.duration_ms)}`,
    timestamp: formatDateTime(item.started_at),
    status: item.status,
  }));
}

const AUDIT_LABELS: Record<string, string> = {
  document_type: "Document type",
  reason_code: "Reason",
  mode: "Mode",
  plan_count: "Plan count",
};

export function auditSummary(event: AuditEventSummary): string {
  const entries = Object.entries(event.metadata)
    .filter(([key]) => key in AUDIT_LABELS)
    .map(([key, value]) => `${AUDIT_LABELS[key]}: ${String(value)}`);
  return entries.length ? entries.join("; ") : "No additional safe details";
}

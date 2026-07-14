export type ReviewStatus =
  | "review_required"
  | "in_review"
  | "corrected"
  | "approved"
  | "rejected"
  | "skipped"
  | "reprocess_requested"
  | "resolved";

export type ReviewPriority = "low" | "normal" | "high" | "urgent";

export interface ReviewCaseSummary {
  review_case_id: string;
  document_id: string;
  reason_code: string;
  priority: ReviewPriority;
  status: ReviewStatus;
  assigned_reviewer: string | null;
  correction_count: number;
  decision_code: string | null;
  reprocess_state: string;
  created_at: string;
  updated_at?: string;
}

export interface CorrectionSummary {
  correction_id: string;
  review_case_id: string;
  field_path: string;
  operation: string;
  reason_code: string;
  actor_id: string;
  occurred_at: string;
  source_stage: string;
}

export interface ReprocessPlanSummary {
  plan_id: string;
  review_case_id: string;
  requested_from_stage: string;
  requested_target_stage: string;
  invalidated_artifact_count: number;
  retained_artifact_count: number;
  reason_code: string;
  requested_by: string;
  created_at: string;
  mode: "dry_run";
}

export interface ReviewListQuery {
  status?: ReviewStatus;
  priority?: ReviewPriority;
  limit?: number;
  offset?: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isBoundedString(value: unknown, maxLength = 256): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= maxLength &&
    !/[\u0000-\u001f\u007f]/.test(value);
}

const REVIEW_STATUSES = new Set<ReviewStatus>([
  "review_required", "in_review", "corrected", "approved", "rejected", "skipped",
  "reprocess_requested", "resolved",
]);
const REVIEW_PRIORITIES = new Set<ReviewPriority>(["low", "normal", "high", "urgent"]);

export function parseReviewCaseSummary(value: unknown): ReviewCaseSummary | null {
  if (!isRecord(value) || !isBoundedString(value.review_case_id, 128) ||
      !isBoundedString(value.document_id, 128) || !isBoundedString(value.reason_code, 128) ||
      !isBoundedString(value.priority, 32) || !REVIEW_PRIORITIES.has(value.priority as ReviewPriority) ||
      !isBoundedString(value.status, 64) || !REVIEW_STATUSES.has(value.status as ReviewStatus) ||
      (value.assigned_reviewer !== null && !isBoundedString(value.assigned_reviewer, 128)) ||
      !Number.isInteger(value.correction_count) || (value.correction_count as number) < 0 ||
      (value.decision_code !== null && !isBoundedString(value.decision_code, 128)) ||
      !isBoundedString(value.reprocess_state, 64) || !isBoundedString(value.created_at, 64)) return null;
  if (value.updated_at !== undefined && !isBoundedString(value.updated_at, 64)) return null;
  return {
    review_case_id: value.review_case_id,
    document_id: value.document_id,
    reason_code: value.reason_code,
    priority: value.priority as ReviewPriority,
    status: value.status as ReviewStatus,
    assigned_reviewer: value.assigned_reviewer as string | null,
    correction_count: value.correction_count as number,
    decision_code: value.decision_code as string | null,
    reprocess_state: value.reprocess_state,
    created_at: value.created_at,
    ...(value.updated_at ? { updated_at: value.updated_at as string } : {}),
  };
}

export function parseCorrectionSummary(value: unknown): CorrectionSummary | null {
  if (!isRecord(value) || !isBoundedString(value.correction_id, 128) ||
      !isBoundedString(value.review_case_id, 128) || !isBoundedString(value.field_path, 128) ||
      !isBoundedString(value.operation, 64) || !isBoundedString(value.reason_code, 128) ||
      !isBoundedString(value.actor_id, 128) || !isBoundedString(value.occurred_at, 64) ||
      !isBoundedString(value.source_stage, 128)) return null;
  return value as unknown as CorrectionSummary;
}

export function parseReprocessPlanSummary(value: unknown): ReprocessPlanSummary | null {
  if (!isRecord(value) || !isBoundedString(value.plan_id, 128) ||
      !isBoundedString(value.review_case_id, 128) || !isBoundedString(value.requested_from_stage, 128) ||
      !isBoundedString(value.requested_target_stage, 128) ||
      !Number.isInteger(value.invalidated_artifact_count) || (value.invalidated_artifact_count as number) < 0 ||
      !Number.isInteger(value.retained_artifact_count) || (value.retained_artifact_count as number) < 0 ||
      !isBoundedString(value.reason_code, 128) || !isBoundedString(value.requested_by, 128) ||
      !isBoundedString(value.created_at, 64) || value.mode !== "dry_run") return null;
  return value as unknown as ReprocessPlanSummary;
}

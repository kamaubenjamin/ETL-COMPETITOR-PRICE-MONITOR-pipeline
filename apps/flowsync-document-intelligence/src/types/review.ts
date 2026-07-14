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


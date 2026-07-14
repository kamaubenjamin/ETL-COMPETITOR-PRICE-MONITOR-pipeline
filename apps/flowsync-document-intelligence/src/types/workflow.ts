export type WorkflowStatus = "queued" | "running" | "succeeded" | "failed";

export interface WorkflowRunSummary {
  run_id: string;
  workflow_name: string;
  status: WorkflowStatus;
  started_at: string;
  duration_ms: number | null;
}

export interface WorkflowListQuery {
  status?: WorkflowStatus;
  limit?: number;
  offset?: number;
}


export type WorkflowStatus = "queued" | "running" | "succeeded" | "failed";

export interface WorkflowRunSummary {
  run_id: string;
  workflow_name: string;
  status: WorkflowStatus;
  started_at: string;
  duration_ms: number | null;
  document_id?: string;
  ended_at?: string;
  workflow_type?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function bounded(value: unknown, max = 256): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= max && !/[\u0000-\u001f\u007f]/.test(value);
}

const WORKFLOW_STATUSES = new Set<WorkflowStatus>(["queued", "running", "succeeded", "failed"]);

export function parseWorkflowRunSummary(value: unknown): WorkflowRunSummary | null {
  if (!isRecord(value) || !bounded(value.run_id, 128) || !bounded(value.workflow_name, 128) ||
      !bounded(value.status, 64) || !WORKFLOW_STATUSES.has(value.status as WorkflowStatus) ||
      !bounded(value.started_at, 64) ||
      (value.duration_ms !== null && (typeof value.duration_ms !== "number" || !Number.isFinite(value.duration_ms) || value.duration_ms < 0))) return null;
  for (const key of ["document_id", "ended_at", "workflow_type"] as const) {
    if (value[key] !== undefined && !bounded(value[key], 128)) return null;
  }
  return value as unknown as WorkflowRunSummary;
}

export interface WorkflowListQuery {
  status?: WorkflowStatus;
  limit?: number;
  offset?: number;
}

import type { JsonScalar } from "./api";

export interface AuditEventSummary {
  event_id: string;
  event_type: string;
  actor_id: string;
  document_id: string | null;
  review_case_id: string | null;
  occurred_at: string;
  metadata: Record<string, JsonScalar>;
}

export interface AuditListQuery {
  event_type?: string;
  limit?: number;
  offset?: number;
}


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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function bounded(value: unknown, max = 256): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= max && !/[\u0000-\u001f\u007f]/.test(value);
}

function isSafeScalar(value: unknown): value is JsonScalar {
  return value === null || typeof value === "boolean" ||
    (typeof value === "number" && Number.isFinite(value)) ||
    (typeof value === "string" && value.length <= 128 && !/[\u0000-\u001f\u007f]/.test(value));
}

const SAFE_METADATA_KEYS = new Set(["document_type", "reason_code", "mode", "plan_count"]);

export function parseAuditEventSummary(value: unknown): AuditEventSummary | null {
  if (!isRecord(value) || !bounded(value.event_id, 128) || !bounded(value.event_type, 128) ||
      !bounded(value.actor_id, 128) ||
      (value.document_id !== null && !bounded(value.document_id, 128)) ||
      (value.review_case_id !== null && !bounded(value.review_case_id, 128)) ||
      !bounded(value.occurred_at, 64) || !isRecord(value.metadata)) return null;
  const metadata: Record<string, JsonScalar> = {};
  for (const [key, item] of Object.entries(value.metadata)) {
    if (SAFE_METADATA_KEYS.has(key) && isSafeScalar(item)) metadata[key] = item;
  }
  return {
    event_id: value.event_id,
    event_type: value.event_type,
    actor_id: value.actor_id,
    document_id: value.document_id as string | null,
    review_case_id: value.review_case_id as string | null,
    occurred_at: value.occurred_at,
    metadata,
  };
}

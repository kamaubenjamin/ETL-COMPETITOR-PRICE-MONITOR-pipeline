export interface ExportAttemptSummary {
  attempt_id: string;
  document_id: string;
  target_id: string;
  target_type: string;
  status: string;
  result_status?: string;
  result_code?: string;
  created_at: string;
  updated_at: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isSafeString(value: unknown, optional = false): value is string | undefined {
  return (optional && value === undefined) || (
    typeof value === "string" && value.length > 0 && value.length <= 256 &&
    !/[\u0000-\u001f\u007f]/.test(value)
  );
}

export function parseExportAttemptSummary(value: unknown): ExportAttemptSummary | null {
  if (!isRecord(value) || !isSafeString(value.attempt_id) || !isSafeString(value.document_id) ||
    !isSafeString(value.target_id) || !isSafeString(value.target_type) || !isSafeString(value.status) ||
    !isSafeString(value.result_status, true) || !isSafeString(value.result_code, true) ||
    !isSafeString(value.created_at) || !isSafeString(value.updated_at)) return null;
  return value as unknown as ExportAttemptSummary;
}

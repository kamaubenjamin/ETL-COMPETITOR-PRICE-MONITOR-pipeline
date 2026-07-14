import { ApiClientError } from "./errors";
import type {
  ApiEnvelope,
  JsonScalar,
  JsonValue,
  PaginationMetadata,
  ResponseMetadata,
  SafeApiErrorPayload,
} from "../types/api";

const ENVELOPE_KEYS = [
  "success",
  "data",
  "error",
  "metadata",
  "api_version",
  "request_id",
] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  return actual.length === expected.length && actual.every((key, index) => key === expected[index]);
}

function isBoundedString(value: unknown, maxLength: number): value is string {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    value.length <= maxLength &&
    !/[\u0000-\u001f\u007f]/.test(value)
  );
}

function isJsonScalar(value: unknown): value is JsonScalar {
  return (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean" ||
    (typeof value === "number" && Number.isFinite(value))
  );
}

function isJsonValue(value: unknown, depth = 0): value is JsonValue {
  if (depth > 12) return false;
  if (isJsonScalar(value)) return true;
  if (Array.isArray(value)) return value.every((item) => isJsonValue(item, depth + 1));
  if (!isRecord(value)) return false;
  return Object.entries(value).every(
    ([key, item]) => key.length <= 128 && isJsonValue(item, depth + 1),
  );
}

function parsePagination(value: unknown): PaginationMetadata | null {
  if (value === null) return null;
  if (!isRecord(value) || !hasExactKeys(value, ["limit", "offset", "total"])) {
    throw ApiClientError.invalidResponse();
  }
  const { limit, offset, total } = value;
  if (
    !Number.isInteger(limit) ||
    !Number.isInteger(offset) ||
    !Number.isInteger(total) ||
    (limit as number) < 1 ||
    (limit as number) > 200 ||
    (offset as number) < 0 ||
    (total as number) < 0
  ) {
    throw ApiClientError.invalidResponse();
  }
  return { limit: limit as number, offset: offset as number, total: total as number };
}

function parseMetadata(value: unknown): ResponseMetadata {
  if (!isRecord(value) || !hasExactKeys(value, ["generated_at", "pagination"])) {
    throw ApiClientError.invalidResponse();
  }
  if (!isBoundedString(value.generated_at, 64) || Number.isNaN(Date.parse(value.generated_at))) {
    throw ApiClientError.invalidResponse();
  }
  return {
    generated_at: value.generated_at,
    pagination: parsePagination(value.pagination),
  };
}

function parseSafeError(value: unknown): SafeApiErrorPayload {
  if (!isRecord(value) || !hasExactKeys(value, ["code", "message", "details"])) {
    throw ApiClientError.invalidResponse();
  }
  if (!isBoundedString(value.code, 64) || !isBoundedString(value.message, 256)) {
    throw ApiClientError.invalidResponse();
  }
  if (!isRecord(value.details) || Object.keys(value.details).length > 10) {
    throw ApiClientError.invalidResponse();
  }
  const details: Record<string, JsonScalar> = {};
  for (const [key, detail] of Object.entries(value.details)) {
    if (!isBoundedString(key, 64) || !isJsonScalar(detail)) {
      throw ApiClientError.invalidResponse();
    }
    if (typeof detail === "string" && detail.length > 128) {
      throw ApiClientError.invalidResponse();
    }
    details[key] = detail;
  }
  return { code: value.code, message: value.message, details };
}

export function parseApiEnvelope<T>(payload: unknown): ApiEnvelope<T> {
  const requestId = isRecord(payload) && typeof payload.request_id === "string"
    ? payload.request_id
    : undefined;
  if (!isRecord(payload) || !hasExactKeys(payload, ENVELOPE_KEYS)) {
    throw ApiClientError.invalidResponse(requestId);
  }
  if (
    typeof payload.success !== "boolean" ||
    payload.api_version !== "v1" ||
    !isBoundedString(payload.request_id, 128) ||
    !isJsonValue(payload.data)
  ) {
    throw ApiClientError.invalidResponse(requestId);
  }

  const metadata = parseMetadata(payload.metadata);
  const error = payload.error === null ? null : parseSafeError(payload.error);
  if ((payload.success && error !== null) || (!payload.success && (error === null || payload.data !== null))) {
    throw ApiClientError.invalidResponse(payload.request_id);
  }

  return {
    success: payload.success,
    data: payload.data as T | null,
    error,
    metadata,
    api_version: "v1",
    request_id: payload.request_id,
  };
}


import type { SafeClientError } from "../api/errors";
import { fixedSafeClientError, toSafeClientError } from "../api/errors";

export type RequestFailureStatus =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "unavailable"
  | "malformed"
  | "safe_error";

export type RequestFailureState = { status: RequestFailureStatus; error: SafeClientError };

export type RequestState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "empty" }
  | RequestFailureState;

export function toRequestFailure(error: unknown): RequestFailureState {
  const safe = toSafeClientError(error);
  const status: RequestFailureStatus = safe.kind === "unauthorized"
    ? "unauthorized"
    : safe.kind === "forbidden"
      ? "forbidden"
      : safe.kind === "not_found"
        ? "not_found"
        : safe.kind === "invalid_response"
          ? "malformed"
          : safe.kind === "invalid_request"
            ? "safe_error"
            : "unavailable";
  return { status, error: safe };
}

export function malformedRequestState(requestId?: string): RequestFailureState {
  return { status: "malformed", error: fixedSafeClientError("invalid_response", requestId) };
}

export function notFoundRequestState(): RequestFailureState {
  return { status: "not_found", error: fixedSafeClientError("not_found") };
}

export function isRequestFailure<T>(state: RequestState<T>): state is RequestFailureState {
  return ["unauthorized", "forbidden", "not_found", "unavailable", "malformed", "safe_error"].includes(state.status);
}

export type SafeClientErrorKind =
  | "invalid_request"
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "unavailable"
  | "runtime_unavailable"
  | "auth_mismatch"
  | "invalid_response";

export interface SafeClientError {
  kind: SafeClientErrorKind;
  code: string;
  message: string;
  requestId?: string;
}

const FIXED_MESSAGES: Record<SafeClientErrorKind, string> = {
  invalid_request: "The request could not be completed.",
  unauthorized: "Sign in is required to continue.",
  forbidden: "You do not have access to this view.",
  not_found: "The requested resource was not found or is unavailable to your access scope.",
  unavailable: "Document Intelligence is temporarily unavailable.",
  runtime_unavailable: "The Document Intelligence runtime is currently unavailable.",
  auth_mismatch: "Document Intelligence access is not configured for this environment.",
  invalid_response: "Document Intelligence returned an invalid response.",
};

const FIXED_CODES: Record<SafeClientErrorKind, string> = {
  invalid_request: "invalid_request",
  unauthorized: "authentication_required",
  forbidden: "access_forbidden",
  not_found: "resource_unavailable",
  unavailable: "api_unavailable",
  runtime_unavailable: "runtime_unavailable",
  auth_mismatch: "auth_configuration_mismatch",
  invalid_response: "invalid_response",
};

function kindForStatus(status: number, code: string): SafeClientErrorKind {
  if (code === "runtime_unavailable") return "runtime_unavailable";
  if (code === "auth_configuration_mismatch" || code === "auth_mismatch") return "auth_mismatch";
  if (status === 400 || status === 405 || status === 422) return "invalid_request";
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  return "unavailable";
}

function boundedRequestId(requestId: string | undefined): string | undefined {
  if (!requestId || requestId.length > 128 || /[\u0000-\u001f\u007f]/.test(requestId)) {
    return undefined;
  }
  return requestId;
}

export class ApiClientError extends Error {
  readonly safe: SafeClientError;

  private constructor(safe: SafeClientError) {
    super(safe.message);
    this.name = "ApiClientError";
    this.safe = Object.freeze({ ...safe });
  }

  static forStatus(status: number, code: string, requestId?: string): ApiClientError {
    const kind = kindForStatus(status, code);
    return new ApiClientError({
      kind,
      code: FIXED_CODES[kind],
      message: FIXED_MESSAGES[kind],
      requestId: boundedRequestId(requestId),
    });
  }

  static unavailable(): ApiClientError {
    return new ApiClientError({
      kind: "unavailable",
      code: "api_unavailable",
      message: FIXED_MESSAGES.unavailable,
    });
  }

  static invalidResponse(requestId?: string): ApiClientError {
    return new ApiClientError({
      kind: "invalid_response",
      code: "invalid_response",
      message: FIXED_MESSAGES.invalid_response,
      requestId: boundedRequestId(requestId),
    });
  }
}

export function fixedSafeClientError(kind: SafeClientErrorKind, requestId?: string): SafeClientError {
  return Object.freeze({
    kind,
    code: FIXED_CODES[kind],
    message: FIXED_MESSAGES[kind],
    requestId: boundedRequestId(requestId),
  });
}

export function toSafeClientError(error: unknown): SafeClientError {
  if (error instanceof ApiClientError) {
    return error.safe;
  }
  return fixedSafeClientError("unavailable");
}

export type SafeClientErrorKind =
  | "invalid_request"
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "unavailable"
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
  not_found: "The requested resource is unavailable.",
  unavailable: "Document Intelligence is temporarily unavailable.",
  invalid_response: "Document Intelligence returned an invalid response.",
};

function kindForStatus(status: number): SafeClientErrorKind {
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
    const kind = kindForStatus(status);
    return new ApiClientError({
      kind,
      code: code || `http_${status}`,
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

export function toSafeClientError(error: unknown): SafeClientError {
  if (error instanceof ApiClientError) {
    return error.safe;
  }
  return Object.freeze({
    kind: "unavailable",
    code: "api_unavailable",
    message: FIXED_MESSAGES.unavailable,
  });
}

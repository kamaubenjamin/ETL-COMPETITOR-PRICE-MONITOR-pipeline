import type { ApiEndpoint } from "./endpoints";
import { ApiClientError } from "./errors";
import { parseApiEnvelope } from "./envelope";
import type { ApiEnvelope } from "../types/api";
import type { UploadMetadataPreviewRequest } from "../types/upload";

export type QueryValue = string | number | boolean | undefined;
export type ApiQuery = Readonly<Record<string, QueryValue>>;

export interface ApiClientOptions {
  baseUrl: string;
  fetchImplementation?: typeof fetch;
}

function validateBaseUrl(value: string): string {
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error("API base URL is invalid");
  }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error("API base URL is invalid");
  }
  return url.toString().replace(/\/$/, "");
}

function appendQuery(url: URL, query: ApiQuery): void {
  const entries = Object.entries(query).filter((entry): entry is [string, string | number | boolean] =>
    entry[1] !== undefined,
  );
  for (const [key, value] of entries.sort(([left], [right]) => left.localeCompare(right))) {
    url.searchParams.set(key, String(value));
  }
}

export class DocumentIntelligenceApiClient {
  private readonly baseUrl: string;
  private readonly fetchImplementation: typeof fetch;

  constructor(options: ApiClientOptions) {
    this.baseUrl = validateBaseUrl(options.baseUrl);
    this.fetchImplementation = options.fetchImplementation ?? fetch;
  }

  async get<T>(endpoint: ApiEndpoint, query: ApiQuery = {}): Promise<ApiEnvelope<T>> {
    const url = new URL(`${this.baseUrl}${endpoint}`);
    appendQuery(url, query);

    let response: Response;
    try {
      response = await this.fetchImplementation(url, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
        credentials: "omit",
      });
    } catch {
      throw ApiClientError.unavailable();
    }

    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      throw ApiClientError.invalidResponse(response.headers.get("X-Request-ID") ?? undefined);
    }

    const envelope = parseApiEnvelope<T>(payload);
    if (!response.ok || !envelope.success) {
      throw ApiClientError.forStatus(
        response.status,
        envelope.error?.code ?? `http_${response.status}`,
        envelope.request_id,
      );
    }
    return envelope;
  }

  async mutate<T>(endpoint: ApiEndpoint, method: "POST" | "PATCH", payload?: unknown): Promise<ApiEnvelope<T>> {
    const url = new URL(`${this.baseUrl}${endpoint}`);
    let response: Response;
    try {
      response = await this.fetchImplementation(url, {
        method,
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        ...(payload === undefined ? {} : { body: JSON.stringify(payload) }),
        cache: "no-store",
        credentials: "omit",
      });
    } catch {
      throw ApiClientError.unavailable();
    }
    let responsePayload: unknown;
    try {
      responsePayload = await response.json();
    } catch {
      throw ApiClientError.invalidResponse(response.headers.get("X-Request-ID") ?? undefined);
    }
    const envelope = parseApiEnvelope<T>(responsePayload);
    if (!response.ok || !envelope.success) {
      throw ApiClientError.forStatus(response.status, envelope.error?.code ?? `http_${response.status}`, envelope.request_id);
    }
    return envelope;
  }

  async validateUploadMetadata<T>(
    endpoint: ApiEndpoint,
    payload: UploadMetadataPreviewRequest,
  ): Promise<ApiEnvelope<T>> {
    const url = new URL(`${this.baseUrl}${endpoint}`);
    let response: Response;
    try {
      response = await this.fetchImplementation(url, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
        credentials: "omit",
      });
    } catch {
      throw ApiClientError.unavailable();
    }

    let responsePayload: unknown;
    try {
      responsePayload = await response.json();
    } catch {
      throw ApiClientError.invalidResponse(response.headers.get("X-Request-ID") ?? undefined);
    }
    const envelope = parseApiEnvelope<T>(responsePayload);
    const governedPreviewCodes = new Set([
      "upload_staging_not_enabled",
      "upload_validation_failed",
      "invalid_upload_metadata",
    ]);
    if (!response.ok && envelope.error && governedPreviewCodes.has(envelope.error.code)) {
      return envelope;
    }
    if (!response.ok || !envelope.success) {
      throw ApiClientError.forStatus(
        response.status,
        envelope.error?.code ?? `http_${response.status}`,
        envelope.request_id,
      );
    }
    return envelope;
  }
}

const DEFAULT_LOCAL_API_URL = "http://127.0.0.1:8001";

export function createApiClient(): DocumentIntelligenceApiClient {
  return new DocumentIntelligenceApiClient({
    baseUrl: import.meta.env.VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL ?? DEFAULT_LOCAL_API_URL,
  });
}

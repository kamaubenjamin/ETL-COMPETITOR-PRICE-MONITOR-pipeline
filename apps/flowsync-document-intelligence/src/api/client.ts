import type { ApiEndpoint } from "./endpoints";
import { ApiClientError } from "./errors";
import { parseApiEnvelope } from "./envelope";
import type { ApiEnvelope } from "../types/api";
import type { UploadMetadataPreviewRequest } from "../types/upload";
import {
  DeploymentConfigurationError,
  documentIntelligenceApiBaseUrl,
  normalizeDocumentIntelligenceApiOrigin,
} from "../config/deploymentEnvironment";
import { getSupabaseAccessToken } from "../auth/supabaseClient";

export type QueryValue = string | number | boolean | undefined;
export type ApiQuery = Readonly<Record<string, QueryValue>>;

export interface ApiClientOptions {
  baseUrl: string;
  fetchImplementation?: typeof fetch;
  accessTokenProvider?: () => Promise<string>;
}

function validateBaseUrl(value: string): string {
  try {
    return normalizeDocumentIntelligenceApiOrigin(value, true);
  } catch (error) {
    if (error instanceof DeploymentConfigurationError) {
      throw ApiClientError.configuration();
    }
    throw new Error("API base URL is invalid");
  }
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
  private readonly accessTokenProvider: () => Promise<string>;

  constructor(options: ApiClientOptions) {
    this.baseUrl = validateBaseUrl(options.baseUrl);
    this.fetchImplementation = options.fetchImplementation ?? fetch;
    this.accessTokenProvider = options.accessTokenProvider ?? getSupabaseAccessToken;
  }

  private async headers(contentType = false): Promise<Record<string, string>> {
    let token: string;
    try {
      token = await this.accessTokenProvider();
    } catch {
      throw ApiClientError.forStatus(401, "authentication_required");
    }
    if (!token || token.length > 16384 || /\s/.test(token)) {
      throw ApiClientError.forStatus(401, "authentication_required");
    }
    return {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
      ...(contentType ? { "Content-Type": "application/json" } : {}),
    };
  }

  async get<T>(endpoint: ApiEndpoint, query: ApiQuery = {}): Promise<ApiEnvelope<T>> {
    const url = new URL(`${this.baseUrl}${endpoint}`);
    appendQuery(url, query);

    const headers = await this.headers();
    let response: Response;
    try {
      response = await this.fetchImplementation(url, {
        method: "GET",
        headers,
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
    const headers = await this.headers(true);
    let response: Response;
    try {
      response = await this.fetchImplementation(url, {
        method,
        headers,
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
    const headers = await this.headers(true);
    let response: Response;
    try {
      response = await this.fetchImplementation(url, {
        method: "POST",
        headers,
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

export function createApiClient(): DocumentIntelligenceApiClient {
  try {
    return new DocumentIntelligenceApiClient({ baseUrl: documentIntelligenceApiBaseUrl() });
  } catch (error) {
    if (error instanceof DeploymentConfigurationError || error instanceof ApiClientError) {
      throw ApiClientError.configuration();
    }
    throw ApiClientError.configuration();
  }
}

export type JsonScalar = string | number | boolean | null;
export type JsonValue = JsonScalar | JsonValue[] | { [key: string]: JsonValue };

export interface PaginationMetadata {
  limit: number;
  offset: number;
  total: number;
}

export interface ResponseMetadata {
  generated_at: string;
  pagination: PaginationMetadata | null;
}

export interface SafeApiErrorPayload {
  code: string;
  message: string;
  details: Record<string, JsonScalar>;
}

export interface ApiEnvelope<T> {
  success: boolean;
  data: T | null;
  error: SafeApiErrorPayload | null;
  metadata: ResponseMetadata;
  api_version: "v1";
  request_id: string;
}

export interface ListQuery {
  limit?: number;
  offset?: number;
}


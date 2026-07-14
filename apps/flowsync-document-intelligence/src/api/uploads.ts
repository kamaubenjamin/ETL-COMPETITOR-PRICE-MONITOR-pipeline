import type { DocumentIntelligenceApiClient } from "./client";
import { API_ENDPOINTS } from "./endpoints";
import { ApiClientError } from "./errors";
import type { ApiEnvelope, JsonScalar } from "../types/api";
import type {
  UploadMetadataPreviewRequest,
  UploadProgressSummary,
  UploadSummary,
  UploadTimeline,
  UploadValidationPreviewResult,
} from "../types/upload";
import { parseUploadProgress, parseUploadSummary, parseUploadTimeline } from "../types/upload";

function parseList<T>(envelope: ApiEnvelope<unknown>, parser: (value: unknown) => T | null): ApiEnvelope<T[]> {
  if (!Array.isArray(envelope.data)) throw ApiClientError.invalidResponse(envelope.request_id);
  const rows = envelope.data.map(parser);
  if (rows.some((row) => row === null)) throw ApiClientError.invalidResponse(envelope.request_id);
  return { ...envelope, data: rows as T[] };
}

function parseOne<T>(envelope: ApiEnvelope<unknown>, parser: (value: unknown) => T | null): ApiEnvelope<T> {
  const data = parser(envelope.data);
  if (!data) throw ApiClientError.invalidResponse(envelope.request_id);
  return { ...envelope, data };
}

export async function listUploads(client: DocumentIntelligenceApiClient) {
  const envelope = await client.get<unknown>(API_ENDPOINTS.uploads, { limit: 50, offset: 0 });
  return parseList<UploadSummary>(envelope, parseUploadSummary);
}

export async function getUploadProgress(client: DocumentIntelligenceApiClient, uploadId: string) {
  return parseOne<UploadProgressSummary>(
    await client.get<unknown>(API_ENDPOINTS.uploadProgress(uploadId)),
    parseUploadProgress,
  );
}

export async function getUploadTimeline(client: DocumentIntelligenceApiClient, uploadId: string) {
  return parseOne<UploadTimeline>(
    await client.get<unknown>(API_ENDPOINTS.uploadTimeline(uploadId)),
    parseUploadTimeline,
  );
}

export async function getDocumentProcessingStatus(client: DocumentIntelligenceApiClient, documentId: string) {
  return parseOne<UploadProgressSummary>(
    await client.get<unknown>(API_ENDPOINTS.documentProcessingStatus(documentId)),
    parseUploadProgress,
  );
}

function safeDetail(details: Record<string, JsonScalar>, key: string): string | null {
  const value = details[key];
  return typeof value === "string" && /^[a-zA-Z0-9_.:-]{1,64}$/.test(value) ? value : null;
}

export async function validateUploadMetadataPreview(
  client: DocumentIntelligenceApiClient,
  request: UploadMetadataPreviewRequest,
): Promise<UploadValidationPreviewResult> {
  const envelope = await client.validateUploadMetadata<unknown>(API_ENDPOINTS.uploadValidationPreview, request);
  if (envelope.success) throw ApiClientError.invalidResponse(envelope.request_id);
  if (envelope.error?.code === "upload_staging_not_enabled") {
    return {
      outcome: "staging_unavailable",
      title: "Metadata validation passed",
      message: "File staging is not enabled yet. The selected file remained in this browser.",
    };
  }
  if (envelope.error?.code === "upload_validation_failed" || envelope.error?.code === "invalid_upload_metadata") {
    return {
      outcome: "invalid",
      title: "Upload metadata needs attention",
      message: "The API did not accept the selected file metadata.",
      issueCode: safeDetail(envelope.error.details, "issue_code"),
      field: safeDetail(envelope.error.details, "field"),
    };
  }
  throw ApiClientError.invalidResponse(envelope.request_id);
}

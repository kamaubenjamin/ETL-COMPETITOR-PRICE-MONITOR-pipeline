import type { DocumentIntelligenceApiClient } from "./client";
import { ApiClientError } from "./errors";
import { API_ENDPOINTS } from "./endpoints";
import type { ApiEnvelope } from "../types/api";
import { parseExportAttemptSummary, type ExportAttemptSummary } from "../types/export";

export async function listDocumentExports(client: DocumentIntelligenceApiClient, documentId: string): Promise<ApiEnvelope<ExportAttemptSummary[]>> {
  const envelope = await client.get<unknown>(API_ENDPOINTS.documentExports(documentId));
  if (!Array.isArray(envelope.data)) throw ApiClientError.invalidResponse(envelope.request_id);
  const attempts = envelope.data.map(parseExportAttemptSummary);
  if (attempts.some((attempt) => attempt === null)) throw ApiClientError.invalidResponse(envelope.request_id);
  return { ...envelope, data: attempts as ExportAttemptSummary[] };
}
